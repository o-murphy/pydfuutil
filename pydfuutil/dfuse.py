"""
This implements the ST Microsystems DFU extensions (DfuSe)
as per the DfuSe 1.1a specification (Document UM0391)
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
import argparse
import sys
from enum import Enum

import usb.util
from construct import Int32ul

from pydfuutil import dfu, dfu_file
from pydfuutil.dfuse_mem import find_segment, DFUSE
from pydfuutil.logger import get_logger
from pydfuutil.portable import milli_sleep

logger = get_logger(__name__)

verbose = False
last_erased = 0
mem_layout: [None, list] = None
dfuse_address = 0
dfuse_length = 0
dfuse_force = False
dfuse_leave = False
dfuse_unprotect = False
dfuse_mass_erase = False

DFU_TIMEOUT = 5000


class DFUSE_COMMAND(Enum):
    SET_ADDRESS = 0x1
    ERASE_PAGE = 0x2
    MASS_ERASE = 0x3
    READ_UNPROTECT = 0x4


def quad2uint(p: bytes) -> int:
    """
    Convert a 4-byte sequence into an unsigned integer (little-endian).
    :param p: 4-byte sequence
    :return: Converted unsigned integer
    """
    return Int32ul.parse(p)


def dfuse_parse_options(options: str) -> None:
    """
    Parse DFU options string and set corresponding flags and values.
    :param options: DFU options string containing address, modifiers, and values.
    :return: None
    """

    global dfuse_address, dfuse_length, dfuse_force, dfuse_leave, dfuse_unprotect, dfuse_mass_erase

    parser = argparse.ArgumentParser(description='Parse DFU options')
    parser.add_argument('--address', type=int, help='DFU address')
    parser.add_argument('--force', action='store_true', help='Force option')
    parser.add_argument('--leave', action='store_true', help='Leave option')
    parser.add_argument('--unprotect', action='store_true', help='Unprotect option')
    parser.add_argument('--mass-erase', action='store_true', help='Mass erase option')
    parser.add_argument('--length', type=int, help='Upload length')

    args, _ = parser.parse_known_args(options.split())

    if args.address is not None:
        dfuse_address = args.address

    if args.force:
        dfuse_force = True

    if args.leave:
        dfuse_leave = True

    if args.unprotect:
        dfuse_unprotect = True

    if args.mass_erase:
        dfuse_mass_erase = True

    if args.length is not None:
        dfuse_length = args.length


def dfuse_special_command(dif: dfu.DFU_IF, address: int, command: DFUSE_COMMAND) -> int:
    """
    Perform DfuSe-specific commands.
    :param dif: DFU interface
    :param address: Address for the command
    :param command: DfuSe command to execute
    :return: None
    """
    buf = bytearray(5)

    length: int
    ret: int
    dst: [dict, None]

    if command == DFUSE_COMMAND.ERASE_PAGE:
        segment = find_segment(mem_layout, address)
        if not segment or not (segment.memtype & DFUSE.DFUSE_ERASABLE):
            logger.error(f"Page at 0x{address:08x} cannot be erased")
            sys.exit(1)
        page_size = segment.pagesize
        if verbose > 1:
            logger.info(
                f"Erasing page size {page_size} at address 0x{address:08x}, page starting at 0x{address & ~(page_size - 1):08x}")
        buf[0] = 0x41  # Erase command
        length = 5
        last_erased = address
    elif command == DFUSE_COMMAND.SET_ADDRESS:
        if verbose > 2:
            logger.debug(f"Setting address pointer to 0x{address:08x}")
        buf[0] = 0x21  # Set Address Pointer command
        length = 5
    elif command == DFUSE_COMMAND.MASS_ERASE:
        buf[0] = 0x41  # Mass erase command when length = 1
        length = 1
    elif command == DFUSE_COMMAND.READ_UNPROTECT:
        buf[0] = 0x92
        length = 1
    else:
        logger.error(f"Non-supported special command {command}")
        sys.exit(1)

    buf[1] = address & 0xff
    buf[2] = (address >> 8) & 0xff
    buf[3] = (address >> 16) & 0xff
    buf[4] = (address >> 24) & 0xff

    ret = dfuse_download(dif, length, buf, 0)
    if ret < 0:
        logger.error("Error during special command download")
        sys.exit(1)

    ret, dst = dfu.dfu_get_status(dif.dev, dif.interface)
    if ret < 0:
        logger.error("Error during special command get_status")
        sys.exit(1)

    if dst.bState != dfu.DFUState.DFU_DOWNLOAD_BUSY:
        logger.error("Wrong state after command download")
        sys.exit(1)

    # Wait while command is executed
    if verbose:
        logger.info(f"Poll timeout {dst.bwPollTimeout} ms")

    milli_sleep(dst.bwPollTimeout)

    if command == DFUSE_COMMAND.READ_UNPROTECT:
        return ret

    ret, dst = dfu.dfu_get_status(dif.dev, dif.interface)
    if ret < 0:
        logger.error("Error during second get_status")
        logger.error(
            f"state({dst.bState}) = {dfu.dfu_state_to_string(dst.bState)}, "
            f"status({dst.bStatus}) = {dfu.dfu_status_to_string(dst.bStatus)}")
        sys.exit(1)

    if dst.bStatus != dfu.DFUStatus.OK:
        logger.error("Command not correctly executed")
        sys.exit(1)

    milli_sleep(dst.bwPollTimeout)

    ret = dfu.dfu_abort(dif.dev, dif.interface)
    if ret < 0:
        logger.error("Error sending dfu abort request")
        sys.exit(1)

    ret, dst = dfu.dfu_get_status(dif.dev, dif.interface)
    if ret < 0:
        logger.error("Error during abort get_status")
        sys.exit(1)

    if dst.bState != dfu.DFUState.DFU_IDLE:
        logger.error("Failed to enter idle state on abort")
        sys.exit(1)

    milli_sleep(dst.bwPollTimeout)
    return ret


def dfuse_upload(dif: dfu.DFU_IF, length: int, data: bytes, transaction: int) -> int:
    """
    DFU_UPLOAD request for DfuSe 1.1a

    :param dif: The USB device handle
    :param length: The length of the data to upload
    :param data: The data buffer to store the uploaded data
    :param transaction: The transaction ID for the upload
    :return: The status of the control transfer
    """
    status = dif.dev.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=dfu.DFUCommands.DFU_UPLOAD,
        wValue=transaction,
        wIndex=dif.interface,
        data_or_wLength=data,
        timeout=DFU_TIMEOUT
    )

    if status < 0:
        logger.error(f"{dfuse_upload.__name__}: libusb_control_msg returned {status}")

    return status


def dfuse_download(dif: dfu.DFU_IF, length: int, data: bytes, transaction: int) -> int:
    """
    DFU_DNLOAD request for DfuSe 1.1a

    :param dif: The DFU interface object.
    :param length: The length of the data to download.
    :param data: The data buffer to download.
    :param transaction: The transaction ID for the download.
    :return: The status of the control transfer.
    """
    status = dif.dev.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=dfu.DFUCommands.DFU_DNLOAD,
        wValue=transaction,
        wIndex=dif.interface,
        data_or_wLength=data,
        timeout=DFU_TIMEOUT
    )

    if status < 0:
        logger.error(f"{dfuse_download.__name__}: libusb_control_transfer returned {status}")

    return status


def dfuse_do_upload(dif: dfu.DFU_IF, xfer_size: int, file: dfu_file.DFUFile, dfuse_options: [str, bytes]) -> int:
    """
    TODO: implementation
    :param dif:
    :param xfer_size:
    :param file:
    :param dfuse_options:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def dfuse_do_dnload(dif: dfu.DFU_IF, xfer_size: int, file: dfu_file.DFUFile, dfuse_options: [str, bytes]) -> int:
    """
    TODO: implementation
    :param dif:
    :param xfer_size:
    :param file:
    :param dfuse_options:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

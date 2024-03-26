"""
This implements the ST Microsystems DFU extensions (DfuSe)
as per the DfuSe 1.1a specification (Document UM0391)
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
import argparse
import errno
import sys
from enum import Enum

import usb.util
from construct import Int32ul

from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile
from pydfuutil.dfuse_mem import find_segment, DFUSE, parse_memory_layout, free_segment_list
from pydfuutil.logger import get_logger
from pydfuutil.portable import milli_sleep

logger = get_logger(__name__)

VERBOSE = False
MEM_LAYOUT: list = []

TIMEOUT = 5000


class Command(Enum):
    """DFUSE commands"""
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


def parse_options(options: str) -> argparse.Namespace:
    """
    Parse DFU options string and set corresponding flags and values.
    :param options: DFU options string containing address, modifiers, and values.
    :return: None
    """

    parser = argparse.ArgumentParser(description='Parse DFU options')
    parser.add_argument('--address', type=int, help='DFU address')
    parser.add_argument('--force', action='store_true', help='Force option')
    parser.add_argument('--leave', action='store_true', help='Leave option')
    parser.add_argument('--unprotect', action='store_true', help='Unprotect option')
    parser.add_argument('--mass-erase', action='store_true', help='Mass erase option')
    parser.add_argument('--length', type=int, help='Upload length')

    args, _ = parser.parse_known_args(options.split())
    return args


def special_command(dif: dfu.DfuIf, address: int, command: Command) -> int:
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

    try:

        if command == Command.ERASE_PAGE:
            segment = find_segment(MEM_LAYOUT, address)
            if not segment or not segment.memtype & DFUSE.ERASABLE:
                raise IOError(f"Page at 0x{address:08x} cannot be erased")

            page_size = segment.pagesize
            if VERBOSE > 1:
                logger.info(
                    f"Erasing page size {page_size} at address 0x{address:08x}, "
                    f"page starting at 0x{address & ~(page_size - 1):08x}")
            buf[0], length = 0x41, 5  # Erase command
            # last_erased = address  # useless?
        elif command == Command.SET_ADDRESS:
            if VERBOSE > 2:
                logger.debug(f"Setting address pointer to 0x{address:08x}")
            buf[0], length = 0x21, 5  # Set Address Pointer command
        elif command == Command.MASS_ERASE:
            buf[0], length = 0x41, 1  # Mass erase command when length = 1
        elif command == Command.READ_UNPROTECT:
            buf[0], length = 0x92, 1
        else:
            raise ValueError(f"Non-supported special command {command}")

        # # overhead
        # buf[1] = address & 0xff; buf[2] = (address >> 8) & 0xff;
        # buf[3] = (address >> 16) & 0xff; buf[4] = (address >> 24) & 0xff

        # for i in range(1, 5):
        #     buf[i] = (address >> (8 * (i - 1))) & 0xFF

        for i in range(0, 4):
            buf[i + 1] = (address >> (8 * i)) & 0xFF

        if download(dif, length, buf, 0) < 0:
            raise IOError("Error during special command download")

        ret, dst = dfu.get_status(dif.dev, dif.interface)
        if ret < 0:
            raise IOError("Error during special command get_status")

        if dst.bState != dfu.State.DFU_DOWNLOAD_BUSY:
            raise IOError("Wrong state after command download")

        # Wait while command is executed
        if VERBOSE:
            logger.info(f"Poll timeout {dst.bwPollTimeout} ms")

        milli_sleep(dst.bwPollTimeout)

        if command == Command.READ_UNPROTECT:
            return ret

        ret, dst = dfu.get_status(dif.dev, dif.interface)
        if ret < 0:
            logger.error(
                f"state({dst.bState}) = {dfu.state_to_string(dst.bState)}, "
                f"status({dst.bStatus}) = {dfu.status_to_string(dst.bStatus)}")
            raise IOError("Error during second get_status")

        if dst.bStatus != dfu.Status.OK:
            raise IOError("Command not correctly executed")

        milli_sleep(dst.bwPollTimeout)

        if dfu.abort(dif.dev, dif.interface) < 0:
            raise IOError("Error sending dfu abort request")

        ret, dst = dfu.get_status(dif.dev, dif.interface)
        if ret < 0:
            raise IOError("Error during abort get_status")

        if dst.bState != dfu.State.DFU_IDLE:
            raise IOError("Failed to enter idle state on abort")

    except (ValueError, IOError) as err:
        logger.error(err)
        sys.exit(1)

    milli_sleep(dst.bwPollTimeout)
    return ret


def upload(dif: dfu.DfuIf, length: int, data: bytes, transaction: int) -> int:
    """
    UPLOAD request for DfuSe 1.1a

    :param dif: The USB device handle
    :param length: The length of the data to upload
    :param data: The data buffer to store the uploaded data
    :param transaction: The transaction ID for the upload
    :return: The status of the control transfer
    """
    status = dif.dev.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN |
                      usb.util.CTRL_TYPE_CLASS |
                      usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=dfu.Command.UPLOAD,
        wValue=transaction,
        wIndex=dif.interface,
        data_or_wLength=data,
        timeout=TIMEOUT
    )

    if status < 0:
        logger.error(f"{upload.__name__}: libusb_control_msg returned {status}")

    return status


def download(dif: dfu.DfuIf, length: int, data: bytes, transaction: int) -> int:
    """
    DNLOAD request for DfuSe 1.1a

    :param dif: The DFU interface object.
    :param length: The length of the data to download.
    :param data: The data buffer to download.
    :param transaction: The transaction ID for the download.
    :return: The status of the control transfer.
    """
    status = dif.dev.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT |
                      usb.util.CTRL_TYPE_CLASS |
                      usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=dfu.Command.DNLOAD,
        wValue=transaction,
        wIndex=dif.interface,
        data_or_wLength=data,
        timeout=TIMEOUT
    )

    if status < 0:
        logger.error(f"{download.__name__}: "
                     f"libusb_control_transfer returned {status}")

    return status


def do_upload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, dfuse_options: [str, bytes]) -> int:
    """
    TODO: implementation
    :param dif:
    :param xfer_size:
    :param file:
    :param dfuse_options:
    :return:
    """

    # pylint: disable=global-statement
    global MEM_LAYOUT

    total_bytes = 0
    upload_limit = 0
    buf = bytearray(xfer_size)
    transaction = 2

    try:
        if dfuse_options:
            parsed_args = parse_options(dfuse_options)
            if parsed_args.length:
                upload_limit = parsed_args.length
        else:
            raise ValueError("No options provided")

        if parsed_args.address:
            # MEM_LAYOUT = parse_memory_layout(dif.alt_name.decode())
            MEM_LAYOUT = parse_memory_layout(dif.alt_name)  # HOTFIX
            if not MEM_LAYOUT:
                raise IOError("Failed to parse memory layout")

            segment = find_segment(MEM_LAYOUT, parsed_args.address)
            if not parsed_args.force and (not segment or not segment.memtype & DFUSE.READABLE):
                raise IOError(f"Page at 0x{parsed_args.address:08x} is not readable")

            if not upload_limit:
                upload_limit = segment.end - parsed_args.address + 1
                logger.info(f"Limiting upload to end of memory segment, {upload_limit} bytes")
            special_command(dif, parsed_args.address, Command.SET_ADDRESS)
        else:
            # Bootloader decides the start address, unknown to us
            # Use a short length to lower risk of running out of bounds
            if not upload_limit:
                upload_limit = 0x4000
            logger.info("Limiting default upload to %i bytes", upload_limit)

        logger.info(f"bytes_per_hash={xfer_size}")
        print("Starting upload: [")
    except (ValueError, IOError) as err:
        logger.error(err)
        return -1

    while True:
        if upload_limit - total_bytes < xfer_size:
            xfer_size = upload_limit - total_bytes
        rc = upload(dif, xfer_size, buf, transaction)
        if rc < 0:
            logger.error("Error during upload")
            ret = rc
            break
        write_rc = file.filep.write(buf[:rc])
        if write_rc < rc:
            logger.error(f"Short file write: {rc}")
            ret = -1
            break
        total_bytes += rc
        if rc < xfer_size or total_bytes >= upload_limit:
            # Last block, return successfully
            ret = total_bytes
            break
        print("#")
        transaction += 1

    print("] finished!")
    return ret


def dnload_chunk(dif: dfu.DfuIf, data: bytes, size: int, transaction: int) -> int:
    """
    Download a chunk of data during DFU download operation.

    :param dif: DfuIf object representing the DFU interface
    :param data: Data to be downloaded
    :param size: Size of the data chunk
    :param transaction: Transaction number
    :return: Number of bytes sent or error code
    """

    ret = download(dif, size, data if size else None, transaction)

    if ret < 0:
        logger.error("Error during download")
        return ret

    bytes_sent = ret

    while True:
        ret, status = dfu.get_status(dif.dev, dif.interface)
        if ret < 0:
            logger.error("Error during download get_status")
            return ret

        # dst = ret # useless?
        milli_sleep(status.bwPollTimeout)

        if status.bState in (dfu.State.DFU_DOWNLOAD_IDLE,
                             dfu.State.DFU_ERROR,
                             dfu.State.DFU_MANIFEST):
            break

    if status.bState == dfu.State.DFU_MANIFEST:
        logger.info("Transitioning to dfuMANIFEST state")

    if status.bStatus != dfu.Status.OK:
        logger.error("Download failed!")
        logger.error("state(%u) = %s, status(%u) = %s", status.bState,
                     dfu.state_to_string(status.bState), status.bStatus,
                     dfu.status_to_string(status.bStatus))
        return -1

    return bytes_sent


# Writes an element of any size to the device, taking care of page erases
# returns 0 on success, otherwise -EINVAL
# pylint: disable=invalid-name
def dnload_element(dif: dfu.DfuIf,
                   dwElementAddress: int,
                   dwElementSize: int,
                   data: bytes,
                   xfer_size: int) -> int:
    """
    Download an element in DFU.

    :param dif: DfuIf object representing the DFU interface
    :param dwElementAddress: Element address
    :param dwElementSize: Size of the element
    :param data: Data to be downloaded
    :param xfer_size: Transfer size
    :return: 0 if successful, error code otherwise
    """

    ret = 0
    segment = find_segment(MEM_LAYOUT, dwElementAddress + dwElementSize - 1)

    if not segment or not segment.memtype & DFUSE.WRITEABLE:
        logger.error(
            f"Error: Last page at 0x{dwElementAddress + dwElementSize - 1:08x} is not writeable"
        )
        return -1

    p = 0
    while p < dwElementSize:
        # page_size = segment.pagesize  # useless?
        address = dwElementAddress + p
        chunk_size = min(xfer_size, dwElementSize - p)

        segment = find_segment(MEM_LAYOUT, address)
        if not segment or not segment.memtype & DFUSE.WRITEABLE:
            logger.error(f"Error: Page at 0x{address:08x} is not writeable")
            return -1

        if VERBOSE:
            logger.info(f"Download from image offset {p:08x} "
                        f"to memory {address:08x}-{address + chunk_size - 1:08x}"
                        f", size {chunk_size}")
        else:
            logger.info(".")

        special_command(dif, address, Command.SET_ADDRESS)

        # transaction = 2 for no address offset
        ret = dnload_chunk(dif, data[p:p + chunk_size], chunk_size, 2)
        if ret != chunk_size:
            logger.error(f"Failed to write whole chunk: {ret} of {chunk_size} bytes")
            return -1

        # Move to the next chunk
        p += xfer_size

    if not VERBOSE:
        logger.info("")

    return ret


# Download raw binary file to DfuSe device
def do_bin_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, start_address: int) -> int:
    """
    Download binary data to the specified address.

    :param dif: DfuIf object representing the DFU interface
    :param xfer_size: Transfer size
    :param file: DFUFile object containing the binary file
    :param start_address: Start address for the download
    :return: Number of bytes read or error code
    """
    dwElementAddress = start_address
    dwElementSize = file.size

    logger.info(f"Downloading to address = 0x{dwElementAddress:08x}, size = {dwElementSize}")

    data = file.filep.read()
    read_bytes = len(data)

    ret = dnload_element(dif, dwElementAddress, dwElementSize, data, xfer_size)
    if ret != 0:
        return ret

    if read_bytes != file.size:
        logger.warning(f"Read {read_bytes} bytes, file size {file.size}")

    logger.info("File downloaded successfully")
    return read_bytes


# Parse a DfuSe file and download contents to device
def do_dfuse_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile) -> int:
    """
    Download data from a DfuSe file to the DFU device.

    :param dif: DfuIf object representing the DFU interface
    :param xfer_size: Transfer size
    :param file: DFUFile object containing the DfuSe file
    :return: Number of bytes read or error code
    """
    dfuprefix = file.filep.read(11)
    read_bytes = len(dfuprefix)

    if dfuprefix != b'DfuSe\x01':
        logger.error("No valid DfuSe signature")
        return -errno.EINVAL

    bTargets = dfuprefix[10]
    logger.info(f"File contains {bTargets} DFU images")

    for image in range(1, bTargets + 1):
        logger.info(f"Parsing DFU image {image}")
        target_prefix = file.filep.read(274)
        read_bytes += len(target_prefix)

        if target_prefix[:6] != b'Target':
            logger.error("No valid target signature")
            return -errno.EINVAL

        bAlternateSetting = target_prefix[6]
        dwNbElements = Int32ul.parse(target_prefix[266:270])
        logger.info(
            f"Image for alternate setting {bAlternateSetting}, "
            f"({dwNbElements} elements, total size = {Int32ul.parse(target_prefix[270:274])})")

        if bAlternateSetting != dif.altsetting:
            logger.warning("Image does not match current alternate setting.")
            logger.warning("Please rerun with the correct -a option setting"
                           " to download this image!")

        for element in range(1, dwNbElements + 1):
            logger.info(f"Parsing element {element}")
            elementheader = file.filep.read(8)
            dwElementAddress, dwElementSize = Int32ul[2].parse(elementheader)
            logger.info(f"Address = 0x{dwElementAddress:08x}, Size = {dwElementSize}")

            # Sanity check
            if read_bytes + dwElementSize + file.suffixlen > file.size:
                logger.error("File too small for element size")
                return -errno.EINVAL

            data = file.filep.read(dwElementSize)
            read_bytes += len(data)

            if bAlternateSetting == dif.altsetting:
                ret = dnload_element(dif, dwElementAddress, dwElementSize, data, xfer_size)
                if ret != 0:
                    return ret

    # Read through the whole file for bookkeeping
    file.filep.read(file.suffixlen)
    read_bytes += file.suffixlen

    if read_bytes != file.size:
        logger.warning(f"Read {read_bytes} bytes, file size {file.size}")

    logger.info("Done parsing DfuSe file")
    return read_bytes


def do_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, dfuse_options: [str, bytes]) -> int:
    """
    Perform DFU download operation.

    :param dif: DfuIf object representing the DFU interface
    :param xfer_size: Transfer size
    :param file: DFUFile object representing the file to be downloaded
    :param dfuse_options: DFU options string containing address, modifiers, and values
    :return: Number of bytes sent or error code
    """

    # pylint: disable=global-statement
    global MEM_LAYOUT
    ret: int

    try:
        if not dfuse_options:
            raise ValueError("No DFUse options provided")

        opts = parse_options(dfuse_options)

        # MEM_LAYOUT = parse_memory_layout(dif.alt_name.decode())
        MEM_LAYOUT = parse_memory_layout(dif.alt_name)  # HOTFIX
        if not MEM_LAYOUT:
            raise IOError("Failed to parse memory layout")

        if opts.unprotect:
            if not opts.force:
                raise PermissionError(
                    "The read unprotect command will erase the flash memory"
                    " and can only be used with force"
                )
            special_command(dif, 0, Command.READ_UNPROTECT)
            logger.info("Device disconnects, erases flash and resets now")
            sys.exit(0)

        if opts.mass_erase:
            if not opts.force:
                raise PermissionError("The mass erase command can only be used with force")
            logger.info("Performing mass erase, this can take a moment")
            special_command(dif, 0, Command.MASS_ERASE)

    except (ValueError, PermissionError, IOError) as err:
        logger.error(err)
        sys.exit(1)

    if opts.address:
        if file.bcdDFU == 0x11a:
            logger.error("This is a DfuSe file, not meant for raw download")
            return -1
        ret = do_bin_dnload(dif, xfer_size, file, opts.address)
    else:
        if file.bcdDFU != 0x11a:
            logger.error("Only DfuSe file version 1.1a is supported"
                         ", (for raw binary download, use the --dfuse-address option)")
            return -1
        ret = do_dfuse_dnload(dif, xfer_size, file)

    free_segment_list(MEM_LAYOUT)

    if opts.leave:
        dnload_chunk(dif, b'', 0, 2)  # Zero-size
        ret2, dst = dfu.get_status(dif.dev, dif.interface)
        if ret2 < 0:
            logger.error("Error during download get_status")
        if VERBOSE:
            logger.info(f"bState = {dst.bState} and bStatus = {dst.bStatus}")

    return ret

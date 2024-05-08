"""
This implements the ST Microsystems DFU extensions (DfuSe)
as per the DfuSe 1.1a specification (Document UM0391)
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import argparse
import sys
from dataclasses import dataclass
from enum import Enum

import usb.util
from usb.backend.libusb1 import LIBUSB_ERROR_PIPE, _strerror

from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile
from pydfuutil.dfuse_mem import find_segment, DFUSE, parse_memory_layout, MemSegment
from pydfuutil.exceptions import GeneralError, MissuseError, _IOError, DataError, NoInputError, ProtocolError
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.progress import Progress
from pydfuutil.quirks import QUIRK

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

MEM_LAYOUT: [MemSegment, None] = None

TIMEOUT = 5000


@dataclass
class RuntimeOptions:
    address: int = None
    address_present: bool = False
    leave: bool = False
    mass_erase: bool = False
    unprotect: bool = False
    will_reset: bool = False
    force: bool = False
    length: int = None
    fast: bool = False


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
    return int.from_bytes(p, byteorder='little', signed=False)


def parse_options(options: list[str]) -> RuntimeOptions:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )

    class ColonSplitAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values.split(':'))

    parser.add_argument('-s', '--dfuse-address', dest='dfuse_address', metavar='<address><:...>',
                        action=ColonSplitAction,
                        help="ST DfuSe mode string, specifying target"
                             "address for raw file download or upload"
                             "(not applicable for DfuSe file (.dfu) downloads)."
                             "Add more DfuSe options separated with ':'\n\n"
                             'leave\n\tLeave DFU mode (jump to application)\n'
                             'mass-erase\n\tErase the whole device (requires "force")\n'
                             'unprotect\n\tErase read protected device (requires "force")\n'
                             'will-reset\n\tExpect device to reset (e.g. option bytes write)\n'
                             'force\n\tYou really know what you are doing!\n'
                             '<length>\n\tLength of firmware to upload from device')

    # parser.print_help()
    args = parser.parse_args(options)

    opts = args.dfuse_address

    rt_opts = RuntimeOptions()

    def atoi(string: str):
        try:
            if string.startswith('0x'):
                return int(string, 16)
            else:
                return int(string)
        except ValueError:
            return None

    if opts is not None:
        if address := atoi(opts[0]):
            rt_opts.address = address
            rt_opts.address_present = True
            opts.pop(0)
        else:
            raise MissuseError(f"Invalid dfuse address: {opts[0]}")

    # Parse other options if any
    for opt in ("force", "leave", "mass_erase", "unprotect", 'will_reset'):
        if opt in opts:
            rt_opts.__setattr__(opt, True)
            opts.pop(opts.index(opt))

    if len(opts) > 1:
        raise MissuseError(f"Too many unexpected dfuse arguments {opts}")

    if len(opts) == 1:
        if length := atoi(opts[0]):
            rt_opts.length = length
        else:
            raise MissuseError(f"Wrong dfuse length: {opts[0]}")
    return rt_opts


def upload(dif: dfu.DfuIf, data: bytes, transaction: int) -> int:
    """
    UPLOAD request for DfuSe 1.1a

    :param dif: The USB device handle
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
        _logger.warning(f"upload: libusb_control_msg returned {status}")

    return status


def download(dif: dfu.DfuIf, data: bytes, transaction: int) -> int:
    """
    DNLOAD request for DfuSe 1.1a

    :param dif: The DFU interface object.
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
        # Silently fail on leave request on some unpredictable devices
        if dif.quirks & QUIRK.DFUSE_LEAVE and not data and transaction == 2:
            return status
        _logger.warning(
            f"download: libusb_control_transfer returned {status}"
        )

    return status


def special_command(dif: dfu.DfuIf, address: int, command: Command, rt_opts: RuntimeOptions) -> int:
    """
    Perform DfuSe-specific commands.
    Leaves the device in dfuDNLOAD-IDLE state
    :param dif: DFU interface
    :param address: Address for the command
    :param command: DfuSe command to execute
    :param rt_opts: RuntimeOptions
    :return: None
    """
    buf = bytearray(5)

    ret: int
    dst: dfu.StatusRetVal
    firstpoll = 1
    zerotimeouts = 0
    polltimeout = 0
    stalls = 0

    try:
        if command == Command.ERASE_PAGE:
            segment = find_segment(dif.mem_layout, address)

            if not segment or not segment.mem_type & DFUSE.ERASABLE:
                raise MissuseError(f"Page at 0x{address:08x} cannot be erased")

            page_size = segment.pagesize
            _logger.debug(
                f"Erasing page size {page_size} at address 0x{address:08x}, "
                f"page starting at 0x{address & ~(page_size - 1):08x}")
            buf[0], length = 0x41, 5  # Erase command
            last_erased_page = address & ~(page_size - 1)
        elif command == Command.SET_ADDRESS:
            _logger.debug(f"Setting address pointer to 0x{address:08x}")
            buf[0], length = 0x21, 5  # Set Address Pointer command
        elif command == Command.MASS_ERASE:
            buf[0], length = 0x41, 1  # Mass erase command when length = 1
        elif command == Command.READ_UNPROTECT:
            buf[0], length = 0x92, 1
        else:
            raise MissuseError(f"Non-supported special command {command}")

        buf[1] = address & 0xff
        buf[2] = (address >> 8) & 0xff
        buf[3] = (address >> 16) & 0xff
        buf[4] = (address >> 24) & 0xff

        ret = download(dif, buf, 0)
        if ret < 0:
            raise _IOError(f"Error during special command {command.name} download: {ret}")

        while True:
            ret = int(dst := dif.get_status())
            # Workaround for some STM32L4 bootloaders that report a too
            # short poll timeout and may stall the pipe when we poll.
            # This also allows "fast" mode (without poll timeouts) to work
            # with many bootloaders

            if ret == LIBUSB_ERROR_PIPE and polltimeout != 0 and stalls < 3:
                dst.bState = dfu.State.DFU_DOWNLOAD_BUSY
                stalls += 1
                _logger.debug("* Device stalled USB pipe, reusing last poll timeout")
            elif ret < 0:
                raise _IOError(f"Error during special command {command.name} get_status: {ret}")
            else:
                polltimeout = dst.bwPollTimeout

            if firstpoll:
                firstpoll = 0
                if dst.bState != dfu.State.DFU_DOWNLOAD_BUSY and dst.bState != dfu.State.DFU_DOWNLOAD_IDLE:
                    _logger.error(f"DFU state({dst.bState}) = {dst.bState.to_string()}, "
                                  f"status({dst.bStatus}) = {dst.bStatus.to_string()}")
                    raise ProtocolError(f"Wrong state after command {command.name} download")
                # STM32F405 lies about mass erase timeout
                if command == Command.MASS_ERASE and dst.bwPollTimeout == 100:
                    polltimeout = 35000  # Datasheet says up to 32 seconds
                    _logger.info("Setting timeout to 35 seconds")

            _logger.debug(f"Err: Poll timeout {polltimeout} "
                          f"ms on command {command.name} (state={dst.bState.to_string()})")
            # A non-null bwPollTimeout for SET_ADDRESS seems a common bootloader bug
            if command == Command.SET_ADDRESS:
                polltimeout = 0
            if not rt_opts.fast and dst.bState == dfu.State.DFU_DOWNLOAD_BUSY:
                milli_sleep(polltimeout)
            if command == Command.READ_UNPROTECT:
                return ret
            # Workaround for e.g. Black Magic Probe getting stuck
            if dst.bwPollTimeout == 0:
                zerotimeouts += 1
                if zerotimeouts == 100:
                    raise _IOError("Device stuck after special command request")
            else:
                zerotimeouts = 0

            if dst.bState != dfu.State.DFU_DOWNLOAD_BUSY:
                break

        if dst.bStatus != dfu.Status.OK:
            raise _IOError(f"{command.name} not correctly executed")

        return 0

    except GeneralError as err:
        if err.__str__:
            _logger.error(err)
        sys.exit(err.exit_code)


def dnload_chunk(dif: dfu.DfuIf, data: bytes, size: int, transaction: int) -> int:
    """
    Download a chunk of data during DFU download operation.

    :param dif: DfuIf object representing the DFU interface
    :param data: Data to be downloaded
    :param size: Size of the data chunk
    :param transaction: Transaction number
    :return: Number of bytes sent or error code
    """

    stalls = 0

    ret = download(dif, data if size else None, transaction)
    if ret < 0:
        raise IOError(f"Error during download: {ret} ({_strerror(ret)})")

    bytes_sent = ret

    while True:
        ret = int(dst := dif.get_status())

        if ret == LIBUSB_ERROR_PIPE and stalls < 3:
            dst.bState = dfu.State.DFU_DOWNLOAD_BUSY
            stalls += 1
            _logger.debug("Err: * Pipe error, retrying get_status")
            continue

        if ret < 0:
            raise _IOError(f"Error during download get_status {ret} ({_strerror(ret)})")

        _logger.debug(f"Err: Poll timeout {dst.bwPollTimeout} "
                      f"ms on download (state={dst.bState.to_string()})")
        if not rt_opts.fast and dst.bState == dfu.State.DFU_DOWNLOAD_BUSY:
            milli_sleep(dst.bwPollTimeout)

        if (dst.bState != dfu.State.DFU_IDLE and
            dst.bState != dfu.State.DFU_ERROR and
            dst.bState != dfu.State.DFU_MANIFEST and
            not (rt_opts.will_reset and dst.bState == dfu.State.DFU_DOWNLOAD_BUSY)):
            break

    if dst.bState == dfu.State.DFU_MANIFEST:
        _logger.info("Transitioning to dfuMANIFEST state")

    if dst.bStatus != dfu.Status.OK:
        _logger.error("Failed!")
        _logger.error(f"DFU state{dst.bState} = {dst.bState.to_string()},"
                      f"status{dst.bStatus} = {dst.bStatus.to_string()}")
        return -1

    return bytes_sent


def do_leave(dif: dfu.DfuIf, rt_opts: RuntimeOptions) -> None:
    """Submitting dfuse leave request"""

    if rt_opts.address_present:
        special_command(dif, rt_opts.address, Command.SET_ADDRESS)
    _logger.info("Submitting leave request...")
    if dif.quirks & QUIRK.DFUSE_LEAVE:
        # The device might leave after this request, with or without a response
        download(dif, 0, None, 2)
        # Or it might leave after this request, with or without a response
        dst = dif.get_status()
    else:
        dnload_chunk(dif, None, 0, 2)


def do_upload():
    # FIXME
    raise NotImplemented


# Writes an element of any size to the device, taking care of page erases
# returns 0 on success, otherwise -EINVAL
# pylint: disable=invalid-name
def dnload_element(dif: dfu.DfuIf,
                   dw_element_address: int,
                   dw_element_size: int,
                   data: bytes,
                   xfer_size: int) -> int:
    """
    Download an element in DFU.

    :param dif: DfuIf object representing the DFU interface
    :param dw_element_address: Element address
    :param dw_element_size: Size of the element
    :param data: Data to be downloaded
    :param xfer_size: Transfer size
    :return: 0 if successful, error code otherwise
    """

    ret = 0
    segment = find_segment(MEM_LAYOUT, dw_element_address + dw_element_size - 1)

    if not segment or not segment.mem_type & DFUSE.WRITEABLE:
        raise MissuseError(
            f"Error: Last page at 0x{dw_element_address + dw_element_size - 1:08x} "
            f"is not writeable"
        )

    p = 0
    while p < dw_element_size:
        address = dw_element_address + p
        chunk_size = min(xfer_size, dw_element_size - p)

        segment = find_segment(MEM_LAYOUT, address)
        if not segment or not segment.mem_type & DFUSE.WRITEABLE:
            raise MissuseError(f"Error: Page at 0x{address:08x} is not writeable")

        _logger.debug(f"Download from image offset {p:08x} "
                      f"to memory {address:08x}-{address + chunk_size - 1:08x}"
                      f", size {chunk_size}")

        special_command(dif, address, Command.SET_ADDRESS)

        # transaction = 2 for no address offset
        ret = dnload_chunk(dif, data[p:p + chunk_size], chunk_size, 2)
        if ret != chunk_size:
            raise _IOError(f"Failed to write whole chunk: {ret} of {chunk_size} bytes")

        # Move to the next chunk
        p += xfer_size

    return ret


def do_bin_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, start_address: int) -> int:
    """
    Download raw binary file to DfuSe device.

    :param dif: DfuIf object representing the DFU interface
    :param xfer_size: Transfer size
    :param file: DFUFile object representing the binary file
    :param start_address: Start address for the download
    :return: 0 if successful, error code otherwise
    """
    dw_element_address = start_address
    dw_element_size = file.size.total - file.size.suffix - file.size.prefix

    _logger.info(f"Downloading element to address = 0x{dw_element_address:08x}, size = {dw_element_size}")

    data = file.firmware[file.size.prefix:]

    ret = dnload_element(dif, dw_element_address, dw_element_size, data, xfer_size)
    if ret == 0:
        _logger.info("File downloaded successfully")

    return ret


def dfuse_memcpy(dst, src, rem, size):
    if size > rem:
        raise ValueError("Corrupt DfuSe file: Cannot read {} bytes from {} bytes".format(size, rem))

    if dst is not None:
        dst.extend(src[:size])

    src[:] = src[size:]
    rem -= size
    return rem


def do_dfuse_dnload(dif, xfer_size, file):
    dfu_prefix = bytearray(11)
    target_prefix = bytearray(274)
    element_header = bytearray(8)

    bFirstAddressSaved = 0

    rem = file.size.total - file.size.prefix - file.size.suffix

    if rem < len(dfu_prefix):
        raise DataError("File too small for a DfuSe file")

    rem = dfuse_memcpy(dfu_prefix, file.firmware, rem, len(dfu_prefix))

    if dfu_prefix[:5] != b'DfuSe':
        raise DataError("No valid DfuSe signature")

    if dfu_prefix[5] != 0x01:
        raise DataError(f"DFU format revision {dfu_prefix[5]} not supported")

    bTargets = dfu_prefix[10]
    _logger.info(f"File contains {bTargets} DFU images")

    for image in range(1, bTargets + 1):
        _logger.info(f"Parsing DFU image {image}")
        rem = dfuse_memcpy(target_prefix, file.firmware, rem, len(target_prefix))

        if target_prefix[:6] != b"Target":
            raise DataError("No valid target signature")

        bAlternateSetting = target_prefix[6]
        if target_prefix[7]:
            _logger.info(f"Target name: {target_prefix[11]}")
        else:
            _logger.info("No target name")

        dwNbElements = quad2uint(target_prefix[270:274])
        _logger.info(f"Image for alternate setting {bAlternateSetting}, "
                     f"(%i elements {dwNbElements}, "
                     f"total size = {target_prefix[266:270]}")

        adif = dif.copy()
        while adif:
            if bAlternateSetting == adif.altsetting:
                adif.dev = dif.dev
                _logger.info(f"Setting Alternate Interface {adif.altsetting}")
                ret = adif.dev.set_altsetting(adif.altsetting)
                if ret < 0:
                    raise _IOError(f"Cannot set alternate interface: {ret}")

                break
            adif = dif.next()

        if not adif:
            _logger.warning(f"No alternate setting {bAlternateSetting} (skipping elements)")

        for element in range(1, dwNbElements + 1):
            _logger.info(f"Parsing element {element}")
            rem = dfuse_memcpy(element_header, file.firmware, rem, len(element_header))

            dwElementAddress = quad2uint(element_header[:4])
            dwElementSize = quad2uint(element_header[4:8])

            _logger.info(f"address = 0x{dwElementAddress:02X}, size = {dwElementSize}")

            if not bFirstAddressSaved:
                bFirstAddressSaved = 1
                dfuse_addr = dwElementAddress  # TODO: Store to rt_opts?

            if dwElementSize > rem:
                raise DataError("File too small for element size")

            if adif:
                ret = dnload_element(
                    adif, dwElementAddress , dwElementSize, file.firmware, xfer_size)

            else:
                ret = 0

            # advance read pointer
            rem = dfuse_memcpy(
                bytearray(dwElementSize), file.firmware,
                rem, dwElementSize
            )

            if ret != 0:
                return ret

    if rem != 0:
        _logger.warning(f"{rem} bytes leftover")

    _logger.info("Done parsing DfuSe file")
    return 0


def dfuse_do_dnload():
    # FIXME
    raise NotImplemented


def multiple_alt(dfu_root: dfu.DfuIf) -> int:
    """
    FIXME: dfu_if is not a generator yet
    Check if we have one interface, possibly multiple alternate interfaces.

    :param dfu_root: DfuIf object representing the root interface
    :return: 1 if there are multiple alternate interfaces, otherwise 0
    """
    dev = dfu_root.dev
    configuration = dfu_root.configuration
    interface = dfu_root.interface
    dif = dfu_root.next

    while dif:
        if dev != dif.dev or configuration != dif.configuration or interface != dif.interface:
            return 0
        dif = dif.next
    return 1


# __all__ = (
    # 'do_upload',
    # 'do_dnload',
    # 'multiple_alt'
# )

"""
DFU transfer routines
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This is supposed to be a general DFU implementation, as specified in the
USB DFU 1.0 and 1.1 specification.

The code was originally intended to interface with a USB device running the
"sam7dfu" firmware (see https://www.openpcd.org/) on an AT91SAM7 processor.

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
import logging

import usb

from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile
from pydfuutil.exceptions import _IOError
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.progress import Progress
from pydfuutil.quirks import QUIRK_POLLTIMEOUT, DEFAULT_POLLTIMEOUT

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


def do_upload(dif: dfu.DfuIf,
              xfer_size: int,
              file: DFUFile = None,
              expected_size: int = -1) -> [int, bytes]:
    """
    Uploads data from DFU device from special page
    :param dif: dfu.dfu_if
    :param xfer_size: chunk size
    :param file: optional - DFUFile object
    :param expected_size: optional - total bytes expected to be uploaded
    :return: uploaded bytes or error code
    """

    _logger.info("Copying data from DFU device to PC")

    total_bytes = 0
    transaction = dfu.TRANSACTION  # start page
    buf = bytearray(xfer_size)

    try:

        with Progress() as progress:
            progress.start_task(
                description="Starting upload",
                total=expected_size if expected_size >= 0 else None
            )
            # ret = 0  # need there?
            while True:
                rc = dif.upload(transaction, buf)

                if len(rc) < 0:
                    _logger.error("Error during upload")
                    ret = rc
                    break

                file.write_crc(0, buf)

                total_bytes += len(rc)

                if total_bytes < 0:
                    raise _IOError("Received too many bytes (wraparound)")

                transaction += 1
                progress.update(advance=len(rc), description="Uploading...")

                # last block, return
                if len(rc) < xfer_size or total_bytes >= expected_size >= 0:
                    ret = total_bytes
                    break

            progress.update(description='Upload finished!')

            _logger.debug(f"Received a total of {total_bytes} bytes")

            if expected_size != 0 and total_bytes != expected_size:
                _logger.warning("Unexpected number of bytes uploaded from device")

            return ret
    except _IOError as e:
        _logger.error(e)
        return -1


# pylint: disable=too-many-branches
def do_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile) -> int:
    """
    :param dif: DfuIf instance
    :param xfer_size: transaction size
    :param file: DFUFile instance
    verbose: is verbose useless cause of using python's logging
    :return:
    """

    buf = file.firmware

    expected_size = file.size.total - file.size.suffix
    bytes_sent = 0

    _logger.info("Copying data from PC to DFU device")

    try:
        with Progress() as progress:
            progress.start_task(
                description="Starting download",
                total=expected_size if expected_size >= 0 else None
            )

            while bytes_sent < expected_size:
                # Note: no idea what's there
                # bytes_left = file.size - file.suffix_len - bytes_sent
                # chunk_size = min(bytes_left, xfer_size)

                if (ret := file.file_p.readinto(buf)) < 0:  # Handle read error
                    raise _IOError(f"Error reading file: {file.name}")

                ret = dif.download(ret, buf[:ret] if ret else None)

                if ret < 0:
                    raise _IOError("Error during download")
                bytes_sent += ret

                while True:
                    if int(status := dif.get_status()) < 0:
                        raise _IOError("Error during download get_status")
                    if status.bState in (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_ERROR):
                        break
                    # Wait while the device executes flashing
                    milli_sleep(
                        DEFAULT_POLLTIMEOUT
                        if dif.quirks & QUIRK_POLLTIMEOUT
                        else status.bwPollTimeout
                    )

                if status.bStatus != dfu.Status.OK:
                    logger.error("Transfer failed!")
                    logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                                f"status({status.bStatus}) = {status.bStatus.to_string()}")
                    raise _IOError("Downloading failed!")

                progress.update(description="Downloading...", advance=xfer_size//1000)

            # Send one zero-sized download request to signalize end
            if dif.download(dfu.TRANSACTION, bytes()) < 0:
                raise _IOError("Error sending completion packet")

            progress.update(description="Download finished!")
            _logger.info("finished!")
            _logger.debug(f"Sent a total of {bytes_sent} bytes")

            # Transition to MANIFEST_SYNC state
            if int(status := dif.get_status()) < 0:
                raise _IOError("Unable to read DFU status")
            _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                         f"status({status.bStatus}) = {status.bStatus.to_string()}")

            if not dif.quirks & QUIRK_POLLTIMEOUT:
                milli_sleep(status.bwPollTimeout)

            # Deal correctly with ManifestationTolerant=0 / WillDetach bits
            while status.bState in (dfu.State.DFU_MANIFEST_SYNC, dfu.State.DFU_MANIFEST):
                # Some devices need some time before we can obtain the status
                milli_sleep(1000)
                if int(status := dif.get_status()) < 0:
                    raise _IOError("Unable to read DFU status")
                _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                             f"status({status.bStatus}) = {status.bStatus.to_string()}")

            if status.bState == dfu.State.DFU_IDLE:
                _logger.info("Done!")
        return bytes_sent

    except _IOError as err:
        _logger.error(err)
        return -1


def init() -> None:
    """Init dfu_load props"""
    dfu.debug(dfu.DEBUG)
    dfu.init(dfu.TIMEOUT)

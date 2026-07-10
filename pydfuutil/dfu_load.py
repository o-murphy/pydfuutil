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
from usb.core import USBError
from pydfuutil import dfu
from pydfuutil.dfu_file import DfuFile
from pydfuutil.exceptions import _IOError, SoftwareError, except_and_safe_exit
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.progress import Progress

_logger = logger.getChild('dfu_load')


@except_and_safe_exit(_logger)
def do_upload(dif: dfu.DfuIf,
              xfer_size: int,
              file: DfuFile,
              expected_size: int = -1) -> int:
    """
    Uploads data from DFU device from special page
    :param dif: dfu.dfu_if
    :param xfer_size: chunk size
    :param file: DfuFile object
    :param expected_size: optional - total bytes expected to be uploaded
    :return: uploaded bytes or error code
    """

    _logger.info("Copying data from DFU device to PC")

    total_bytes = 0
    transaction = dfu.TRANSACTION  # start page

    with Progress() as progress:
        progress.start_task(
            description="Starting upload",
            total=expected_size if expected_size >= 0 else None
        )
        while True:
            try:
                rc = dif.upload(transaction, xfer_size)
            except USBError as e:
                _logger.error(f"Error during upload: {e}")
                ret = e.backend_error_code if e.backend_error_code is not None else -1
                progress.update(description='Upload failed!')
                break

            file.write_crc(0, rc)

            total_bytes += len(rc)

            if total_bytes < 0:
                progress.update(description='Upload failed!')
                progress.fail()
                raise SoftwareError("Received too many bytes (wraparound)")

            transaction += 1
            progress.update(advance=len(rc), description="Uploading...")

            # last block, return
            if len(rc) < xfer_size:
                ret = total_bytes
                break

        _logger.debug(f"Received a total of {total_bytes} bytes")

        if ret < 0:
            progress.update(description='Upload failed!')
            progress.fail()
            return ret

        if expected_size not in (0, total_bytes):
            progress.update(description='Upload failed!')
            progress.fail()
            _logger.error("Unexpected number of bytes uploaded from device")
            return ret

        progress.update(description='Upload finished!')

        return ret


# pylint: disable=too-many-branches
@except_and_safe_exit(_logger)
def do_download(dif: dfu.DfuIf, xfer_size: int, file: DfuFile) -> int:
    """
    :param dif: DfuIf instance
    :param xfer_size: transaction size
    :param file: DfuFile instance
    verbose: is verbose useless cause of using python's logging
    :return:
    """

    buf = file.firmware

    expected_size = file.size.total - file.size.suffix
    bytes_sent = 0
    transaction = dfu.TRANSACTION

    _logger.info("Copying data from PC to DFU device")

    with Progress() as progress:
        progress.start_task(
            description="Starting download",
            total=expected_size if expected_size >= 0 else None
        )

        while bytes_sent < expected_size:
            bytes_left = expected_size - bytes_sent
            chunk_size = min(bytes_left, xfer_size)

            try:
                dif.download(
                    transaction,
                    buf[bytes_sent:bytes_sent + chunk_size] if chunk_size else None
                )
            except USBError as e:
                raise _IOError(f"Error during download: {e}") from e
            bytes_sent += chunk_size
            transaction += 1

            while True:
                try:
                    status = dif.get_status()
                except USBError as e:
                    raise _IOError(f"Error during download get_status {e}") from e
                if status.bState in (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_ERROR):
                    break
                # Wait while the device executes flashing
                # (bwPollTimeout is already quirk-adjusted by dif.get_status())
                milli_sleep(status.bwPollTimeout)

            if status.bStatus != dfu.Status.OK:
                logger.error("Transfer failed!")
                logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                            f"status({status.bStatus}) = {status.bStatus.to_string()}")
                raise _IOError("Downloading failed!")

            progress.update(description="Downloading...", advance=chunk_size)

        # Send one zero-sized download request to signalize end
        try:
            dif.download(transaction, bytes())
        except USBError as e:
            raise _IOError(f"Error sending completion packet {e}") from e

        progress.update(description="Download finished!")
        _logger.info("finished!")
        _logger.debug(f"Sent a total of {bytes_sent} bytes")

        # Transition to MANIFEST_SYNC state
        try:
            status = dif.get_status()
        except USBError as e:
            raise _IOError(f"Unable to read DFU status: {e}") from e
        _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                     f"status({status.bStatus}) = {status.bStatus.to_string()}")

        # (bwPollTimeout is already quirk-adjusted by dif.get_status())
        milli_sleep(status.bwPollTimeout)

        # Deal correctly with ManifestationTolerant=0 / WillDetach bits
        while status.bState in (dfu.State.DFU_MANIFEST_SYNC, dfu.State.DFU_MANIFEST):
            # Some devices need some time before we can obtain the status
            milli_sleep(1000)
            try:
                status = dif.get_status()
            except USBError as e:
                raise _IOError(f"Unable to read DFU status: {e}") from e
            _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                         f"status({status.bStatus}) = {status.bStatus.to_string()}")
            # (bwPollTimeout is already quirk-adjusted by dif.get_status())
            milli_sleep(status.bwPollTimeout)

        if status.bState == dfu.State.DFU_MANIFEST_WAIT_RESET:
            _logger.info("Resetting USB to switch back to runtime mode")
            assert dif.dev is not None
            try:
                dif.dev.reset()
            except USBError as e:
                _logger.warning(f"error resetting after download: {e}")
        elif status.bState == dfu.State.DFU_IDLE:
            _logger.info("Done!")
    return bytes_sent


__all__ = (
    'do_upload',
    'do_download'
)

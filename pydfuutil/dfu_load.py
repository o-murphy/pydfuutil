"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
import logging

from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.progress import Progress
from pydfuutil.quirks import QUIRK_POLLTIMEOUT, DEFAULT_POLLTIMEOUT

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


def do_upload(dif: dfu.DfuIf,
              xfer_size: int,
              file: DFUFile = None,
              total_size: int = -1) -> [int, bytes]:
    """
    Uploads data from DFU device from special page
    :param dif: dfu.dfu_if
    :param xfer_size: chunk size
    :param file: optional - DFUFile object
    :param total_size: optional - total bytes expected to be uploaded
    :return: uploaded bytes or error code
    """

    _logger.info(f"bytes_per_hash={xfer_size}")
    _logger.info("Copying data from DFU device to PC")

    total_bytes = 0
    transaction = dfu.TRANSACTION  # start page
    buf = bytearray(xfer_size)

    with Progress() as progress:
        progress.start_task(
            description="Starting upload",
            total=total_size if total_size >= 0 else None
        )

        while True:
            rc = dif.upload(transaction, buf)

            if len(rc) < 0:
                ret = rc
                break

            if file:
                write_rc = file.file_p.write(rc)

                if write_rc < len(rc):
                    _logger.error(f'Short file write: {write_rc}')
                    ret = total_bytes
                    break

            total_bytes += len(rc)

            transaction += 1
            progress.update(advance=xfer_size, description="Uploading...")

            # last block, return
            if (len(rc) < xfer_size) or (total_bytes >= total_size >= 0):
                ret = total_bytes
                break

        progress.update(description='Upload finished!')

        _logger.debug(f"Received a total of {total_bytes} bytes")
        return ret


# pylint: disable=too-many-branches
def do_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, quirks: int, verbose: bool) -> int:
    """
    :param dif: DfuIf instance
    :param xfer_size: transaction size
    :param file: DFUFile instance
    :param quirks: quirks
    :param verbose: is verbose
    :return:
    """

    _logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    bytes_sent = 0
    buf = bytearray(xfer_size)

    _logger.info("Copying data from PC to DFU device")
    _logger.info("Starting download: ")
    try:

        with Progress() as progress:
            total_size = file.size - file.suffix_len
            progress.start_task(
                description="Starting download",
                total=total_size if total_size >= 0 else None
            )

            while bytes_sent < file.size - file.suffix_len:
                # Note: no idea what's there
                # bytes_left = file.size - file.suffix_len - bytes_sent
                # chunk_size = min(bytes_left, xfer_size)

                if (ret := file.file_p.readinto(buf)) < 0:  # Handle read error
                    raise IOError(f"Error reading file: {file.name}")

                ret = dif.download(ret, buf[:ret] if ret else None)

                if ret < 0:
                    raise IOError("Error during download")
                bytes_sent += ret

                while True:
                    if int(status := dif.get_status()) < 0:
                        raise IOError("Error during download get_status")
                    if status.bState in (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_ERROR):
                        break
                    # Wait while the device executes flashing
                    milli_sleep(
                        DEFAULT_POLLTIMEOUT
                        if quirks & QUIRK_POLLTIMEOUT
                        else status.bwPollTimeout
                    )

                if status.bStatus != dfu.Status.OK:
                    logger.error("Transfer failed!")
                    print(f"state({status.bState}) = {status.bState.to_string()}, "
                          f"status({status.bStatus}) = {status.bStatus.to_string()}")
                    raise IOError("Downloading failed!")

                progress.update(description="Downloading...", advance=xfer_size)

            # Send one zero-sized download request to signalize end
            if dif.download(dfu.TRANSACTION, bytes()) < 0:
                raise IOError("Error sending completion packet")

            progress.update(description="Download finished!")
            _logger.info("finished!")
            _logger.debug(f"Sent a total of {bytes_sent} bytes")

            # Transition to MANIFEST_SYNC state
            if int(status := dif.get_status()) < 0:
                raise IOError("Unable to read DFU status")
            _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                         f"status({status.bStatus}) = {status.bStatus.to_string()}")

            if not quirks & QUIRK_POLLTIMEOUT:
                milli_sleep(status.bwPollTimeout)

            # Deal correctly with ManifestationTolerant=0 / WillDetach bits
            while status.bState in (dfu.State.DFU_MANIFEST_SYNC, dfu.State.DFU_MANIFEST):
                # Some devices need some time before we can obtain the status
                milli_sleep(1000)
                if int(status := dif.get_status()) < 0:
                    raise IOError("Unable to read DFU status")
                _logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                             f"status({status.bStatus}) = {status.bStatus.to_string()}")

            if status.bState == dfu.State.DFU_IDLE:
                _logger.info("Done!")

    except IOError as err:
        _logger.error(err)
        return -1

    return bytes_sent


def init() -> None:
    """Init dfu_load props"""
    dfu.debug(dfu.DEBUG)
    dfu.init(dfu.TIMEOUT)

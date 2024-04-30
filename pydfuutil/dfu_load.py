"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
import logging

from rich import progress

from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile
from pydfuutil.logger import get_logger
from pydfuutil.portable import milli_sleep
from pydfuutil.quirks import QUIRK_POLLTIMEOUT, DEFAULT_POLLTIMEOUT

logger = get_logger(__name__)

# VERBOSE: bool = False  # useless?

_progress_bar = progress.Progress(
    progress.TextColumn("[progress.description]{task.description}"),
    progress.BarColumn(20),
    progress.TaskProgressColumn(),
    progress.TimeRemainingColumn(),
    progress.DownloadColumn(),
    progress.TransferSpeedColumn(),
)

PROGRESS_BAR_WIDTH = 50


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

    logger.info(f"bytes_per_hash={xfer_size}")
    logger.info("Copying data from DFU device to PC")

    upload_task = _progress_bar.add_task(
        '[magenta1]Starting upload',
        total=total_size if total_size >= 0 else None
    )

    total_bytes = 0
    transaction = dfu.TRANSACTION  # start page
    buf = bytearray(xfer_size)

    while True:
        rc = dfu.upload(
            device=dif.dev,
            interface=dif.interface,
            transaction=transaction,
            data_or_length=buf
        )

        if len(rc) < 0:
            ret = rc
            break

        if file:
            write_rc = file.filep.write(rc)

            if write_rc < len(rc):
                logger.error(f'Short file write: {write_rc}')
                ret = total_bytes
                break

        total_bytes += len(rc)

        # last block, return
        if (len(rc) < xfer_size) or (total_bytes >= total_size >= 0):
            ret = total_bytes
            break

        transaction += 1
        # _progress_bar.update(upload_task, advance=xfer_size)
        _progress_bar.update(upload_task, advance=xfer_size, description='[magenta1]Uploading...')

    _progress_bar.update(upload_task, description='[yellow4]Upload finished!')
    _progress_bar.stop()
    _progress_bar.remove_task(upload_task)

    logger.debug(f"Received a total of {total_bytes} bytes")
    return ret


def do_dnload(dif: dfu.DfuIf, xfer_size: int, file: DFUFile, quirks: int, verbose: bool) -> int:
    """
    :param dif: DfuIf instance
    :param xfer_size: transaction size
    :param file: DFUFile instance
    :param quirks: quirks
    :param verbose: is verbose
    :return:
    """

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    bytes_sent = 0
    buf = bytearray(xfer_size)

    bytes_per_hash = (file.size - file.suffixlen) // PROGRESS_BAR_WIDTH
    if bytes_per_hash == 0:
        bytes_per_hash = 1
    logger.info(f"bytes_per_hash={bytes_per_hash}")

    logger.info("Copying data from PC to DFU device")
    logger.info("Starting download: ")
    print("[", end="")

    try:
        while bytes_sent < file.size - file.suffixlen:
            # FIXME: no idea what's there
            # bytes_left = file.size - file.suffixlen - bytes_sent
            # chunk_size = min(bytes_left, xfer_size)

            if (ret := file.filep.readinto(buf)) < 0:  # Handle read error
                raise IOError(f"Error reading file: {file.name}")

            ret = dfu.download(dif.dev, dif.interface, ret, buf[:ret] if ret else None)

            if ret < 0:
                raise IOError("Error during download")
            bytes_sent += ret

            while True:
                if int(status := dfu.get_status(dif.dev, dif.interface)) < 0:
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
                print(" failed!")
                print(f"state({status.bState}) = {status.bState.to_string()}, "
                      f"status({status.bStatus}) = {status.bStatus.to_string()}")
                raise IOError("Failed")

            print("#" * (bytes_sent // bytes_per_hash), end="")

        # Send one zero-sized download request to signalize end
        if dfu.download(dif.dev, dif.interface, dfu.TRANSACTION, bytes()) < 0:
            raise IOError("Error sending completion packet")

        print("]")
        logger.info("finished!")
        logger.debug(f"Sent a total of {bytes_sent} bytes")

        # Transition to MANIFEST_SYNC state
        if int(status := dfu.get_status(dif.dev, dif.interface)) < 0:
            raise IOError("Unable to read DFU status")
        logger.info(f"state({status.bState}) = {status.bState.to_string()}, "
                    f"status({status.bStatus}) = {status.bStatus.to_string()}")

        if not quirks & QUIRK_POLLTIMEOUT:
            milli_sleep(status.bwPollTimeout)

        # Deal correctly with ManifestationTolerant=0 / WillDetach bits
        while status.bState in (dfu.State.DFU_MANIFEST_SYNC, dfu.State.DFU_MANIFEST):
            # Some devices need some time before we can obtain the status
            milli_sleep(1000)
            if int(status := dfu.get_status(dif.dev, dif.interface)) < 0:
                raise IOError("Unable to read DFU status")
            print(f"state({status.bState}) = {status.bState.to_string()}, "
                  f"status({status.bStatus}) = {status.bStatus.to_string()}")

        if status.bState == dfu.State.DFU_IDLE:
            logger.info("Done!")

    except IOError as err:
        logger.error(err)
        return -1

    return bytes_sent


def init() -> None:
    """Init dfu_load props"""
    dfu.debug(dfu.DEBUG)
    dfu.init(dfu.TIMEOUT)

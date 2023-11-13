"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

from rich import progress

from pydfuutil.dfu import *
from pydfuutil.dfu_file import *
from pydfuutil.portable import *
from pydfuutil.quirks import *

verbose: int = 0

_progress_bar = progress.Progress(
    progress.TextColumn("[progress.description]{task.description}"),
    progress.BarColumn(20),
    progress.TaskProgressColumn(),
    progress.TimeRemainingColumn(),
    progress.DownloadColumn(),
    progress.TransferSpeedColumn(),
)

PROGRESS_BAR_WIDTH = 50


def dfuload_do_upload(dif: DFU_IF,
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
    transaction = DFU_TRANSACTION  # start page
    buf = bytearray(xfer_size)

    while True:
        rc = dfu_upload(
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

    if verbose:
        logger.info(f"Received a total of {total_bytes} bytes")
    return ret


#     download_task = _progress_bar.add_task(
#         '[magenta1]Starting upload',
#         total=total_size if total_size >= 0 else None
#     )


def dfuload_do_dnload(dif: DFU_IF, xfer_size: int, file: DFUFile, quirks: int, verbose: bool) -> int:
    bytes_sent = 0
    buf = bytearray(xfer_size)

    bytes_per_hash = (file.size - file.suffixlen) // PROGRESS_BAR_WIDTH
    if bytes_per_hash == 0:
        bytes_per_hash = 1
    logger.info(f"bytes_per_hash={bytes_per_hash}")

    logger.info("Copying data from PC to DFU device")
    logger.info("Starting download: ")
    print("[", end="")
    while bytes_sent < file.size - file.suffixlen:
        bytes_left = file.size - file.suffixlen - bytes_sent
        chunk_size = min(bytes_left, xfer_size)  # TODO: no idea what's there

        ret = file.filep.readinto(buf)
        if ret < 0:
            # Handle read error
            logger.error(f"Error reading file: {file.name}")
            return -1

        ret = dfu_download(dif.dev, dif.interface, ret, buf[:ret] if ret else None)

        if ret < 0:
            logger.error("Error during download")
            return -1
        bytes_sent += ret

        while True:
            ret, status = dfu_get_status(dif.dev, dif.interface)
            if ret < 0:
                logger.error("Error during download get_status")
                return -1
            if status.bState == DFUState.DFU_DOWNLOAD_IDLE or status.bState == DFUState.DFU_ERROR:
                break
            # Wait while the device executes flashing
            if quirks & QUIRK_POLLTIMEOUT:
                milli_sleep(DEFAULT_POLLTIMEOUT)
            else:
                milli_sleep(status.bwPollTimeout)

        if status.bStatus != DFUStatus.OK:
            print(" failed!")
            print(f"state({status.bState}) = {dfu_state_to_string(status.bState)}, "
                  f"status({status.bStatus}) = {dfu_status_to_string(status.bStatus)}")
            return -1

        hashes_todo = (bytes_sent // bytes_per_hash)
        while hashes_todo:
            print("#", end="")
            hashes_todo -= 1

    # Send one zero-sized download request to signalize end
    ret = dfu_download(dif.dev, dif.interface, DFU_TRANSACTION, bytes())
    if ret < 0:
        logger.error("Error sending completion packet")
        return -1

    print("]")
    logger.info("finished!")
    if verbose:
        logger.info(f"Sent a total of {bytes_sent} bytes")

    # Transition to MANIFEST_SYNC state
    ret, status = dfu_get_status(dif.dev, dif.interface)
    if ret < 0:
        logger.error("Unable to read DFU status")
        return -1
    logger.info(f"state({status.bState}) = {dfu_state_to_string(status.bState)}, "
                f"status({status.bStatus}) = {dfu_status_to_string(status.bStatus)}")

    if not (quirks & QUIRK_POLLTIMEOUT):
        milli_sleep(status.bwPollTimeout)

    # Deal correctly with ManifestationTolerant=0 / WillDetach bits
    while status.bState in {DFUState.DFU_MANIFEST_SYNC, DFUState.DFU_MANIFEST}:
        # Some devices need some time before we can obtain the status
        milli_sleep(1000)
        ret, status = dfu_get_status(dif.dev, dif.interface)
        if ret < 0:
            logger.error("Unable to read DFU status")
            return -1
        print(f"state({status.bState}) = {dfu_state_to_string(status.bState)}, "
              f"status({status.bStatus}) = {dfu_status_to_string(status.bStatus)}")

    if status.bState == DFUState.DFU_IDLE:
        logger.info("Done!")

    return bytes_sent


def dfuload_init() -> None:
    dfu_debug(DEBUG)
    dfu_init(DFU_TIMEOUT)

from pydfuutil.dfu import *
from pydfuutil.dfu import DFU_TRANSACTION
import logging
from rich import progress


logger = logging.getLogger(__name__)

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
                      file: 'dfu_file.file' = None,
                      total_size: int = -1) -> [int, bytes]:
    """
    Uploads data from DFU device from special page
    TODO: add rich progress bar
    :param dif: dfu.dfu_if
    :param xfer_size: chunk size
    :param file: optional - io.BytesIO object
    :param total_size: optional - total bytes expected to be upload
    :return: uploaded bytes or error code
    """

    logger.info("bytes_per_hash={xfer_size}", xfer_size)
    logger.info("Copying data from DFU device to PC")

    upload_task = _progress_bar.add_task(
        '[magenta1]Starting upload',
        total=total_size if total_size >= 0 else None
    )

    total_bytes = 0
    transaction = DFU_TRANSACTION  # start page

    while True:
        rc = dfu_upload(
            device=dif.dev,
            interface=dif.interface,
            transaction=transaction,
            data_or_length=bytes(xfer_size)
        )

        if len(rc) < 0:
            ret = rc
            break

        if file:
            write_rc = len(rc)  # TODO: write_rc = file.write(rc)
            if write_rc < len(rc):
                logger.error(f'Short file write: {write_rc}')
                ret = total_bytes
                break

        total_bytes += len(rc)

        # /* last block, return */
        if (len(rc) < xfer_size) or (total_bytes >= total_size >= 0):
            ret = total_bytes
            break

        transaction += 1
        _progress_bar.update(upload_task, advance=xfer_size)
        _progress_bar.update(upload_task, advance=xfer_size, description='[magenta1]Uploading...')

    _progress_bar.update(upload_task, description='[yellow4]Upload finished!')
    _progress_bar.stop()
    _progress_bar.remove_task(upload_task)

    if verbose:
        logger.info(f"Received a total of {total_bytes} bytes")
    return ret


# def dfuload_do_dnload(dif: DFU_IF, xfer_size: int, file: 'dfu_file.file') -> int:
#     bytes_sent: int = 0
#     buf: [bytes, int]
#     dst: dfu_status
#
#     buf = bytes(xfer_size)
#     bytes_per_hash = (file.size - file.suffixlen) / PROGRESS_BAR_WIDTH
#     if bytes_per_hash == 0:
#         bytes_per_hash = 1
#
#     logger.info(f"bytes_per_hash={bytes_per_hash}")
#
#     logger.info("Copying data from PC to DFU device")
#
#     # download_task = _progress_bar.add_task(
#     #     '[magenta1]Starting upload',
#     #     total=total_size if total_size >= 0 else None
#     # )
#
#     while bytes_sent < file.size - file.suffixlen - bytes_sent:
#         hashes_todo: int
#         bytes_left: int
#         chunk_size: int
#
#         bytes_left = file.size - file.suffixlen - bytes_sent
#         if bytes_left < xfer_size:
#             chunk_size = bytes_left
#
#         else:
#             chunk_size = xfer_size
#
#         ret = file.read(chunk_size)
#         if len(ret) < 0:
#             logger.error(f'{file.name}')
#             ret = bytes_sent
#             break
#
#         ret = dfu_download(device=dif.dev,
#                            interface=dif.interface,
#                            )


def dfuload_init() -> None:
    dfu_debug(DEBUG)

import io
from pydfuutil.dfu import *
import logging


logger = logging.getLogger(__name__)

verbose: int = 0

PROGRESS_BAR_WIDTH = 50


def dfuload_do_upload(dif: dfu_if, xfer_size: int, file: [io.FileIO, io.BytesIO] = None) -> [int, bytes]:
    """
    TODO: add rich progress bar
    :param dif:
    :param xfer_size:
    :param file:
    :return:
    """
    buf = bytes(xfer_size)
    if not buf:
        raise MemoryError

    logger.info("bytes_per_hash={xfer_size}", xfer_size)
    logger.info("Copying data from DFU device to PC")
    print("Starting upload: [", end='')

    total_bytes = 0
    ret = 0

    while True:
        rc = dfu_upload(dif.dev, dif.interface, xfer_size, buf)

        if len(rc) < 0:
            ret = rc
            break

        if file:
            write_rc = file.write(rc)
            if write_rc < len(rc):
                logger.error(f'Short file write: {write_rc}')
                ret = total_bytes
                break

        total_bytes += len(rc)

        # /* last block, return */
        if len(rc) < xfer_size:
            ret = total_bytes
            break

        print('#', end='')

    print("] finished!")
    if verbose:
        logger.info(f"Received a total of {total_bytes} bytes")
    return ret

dfuload_do_upload()

def dfuload_do_dnload(dif: dfu_if, xfer_size: int, file: [io.FileIO, io.BytesIO] = None) -> int:
    pass


def dfuload_init() -> None:
    pass

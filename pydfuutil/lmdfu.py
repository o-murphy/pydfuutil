"""
This implements the TI Stellaris DFU
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

as per the Application Update Using the USB Device Firmware Upgrade Class
(Document AN012373)
https://www.ti.com/general/docs/lit/getliterature.tsp?literatureNumber=spma003&fileType=pdf
"""

from pydfuutil.dfu_file import DFUFile, parse_dfu_suffix, generate_dfu_suffix
from pydfuutil.logger import logger

__all__ = ('dfu_prefix',
           'add_prefix',
           'remove_prefix',
           'check_prefix',
           'parse_dfu_suffix',
           'generate_dfu_suffix')

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

# dfu_prefix payload length excludes prefix and suffix


dfu_prefix = (
    0x01,  # STELLARIS_DFU_PROG
    0x00,  # Reserved
    0x00,  # LSB start address / 1024
    0x20,  # MSB start address / 1024
    0x00,  # LSB file payload length
    0x00,  # Byte 2 file payload length
    0x00,  # Byte 3 file payload length
    0x00,  # MSB file payload length
)


def add_prefix(file: DFUFile, address: int) -> int:
    """
    Add TI Stellaris DFU prefix to a binary file.

    :param file: DFUFile instance representing the file to be modified.
    :param address: Integer representing the starting address for the TI Stellaris DFU prefix.
    :return: 0 on success, -1 on error.
    """

    try:
        # Get file length
        file.file_p.seek(0, 2)
        length = file.file_p.tell()
        file.file_p.seek(0, 0)

        # Read file content
        data = file.file_p.read()

        # Allocate buffer
        lmdfu_dfu_prefix_buf = bytearray([0] * 16)

        # Fill Stellaris dfu_prefix with correct data
        addr = address // 1024
        lmdfu_dfu_prefix_buf[2] = addr & 0xff
        lmdfu_dfu_prefix_buf[3] = (addr >> 8) & 0xff
        lmdfu_dfu_prefix_buf[4] = length & 0xff
        lmdfu_dfu_prefix_buf[5] = (length >> 8) & 0xff
        lmdfu_dfu_prefix_buf[6] = (length >> 16) & 0xff
        lmdfu_dfu_prefix_buf[7] = (length >> 24) & 0xff

        # Write TI Stellaris DFU prefix to the file
        file.file_p.seek(0)
        file.file_p.write(lmdfu_dfu_prefix_buf)

        # Write file content after the TI Stellaris DFU prefix
        file.file_p.write(data)

        _logger.info("TI Stellaris DFU prefix added.")

        return 0
    except Exception as e:
        _logger.error(f"Error: {e}")
        return -1


def remove_prefix(file: DFUFile) -> int:
    """
    Remove TI Stellaris DFU prefix from a binary file.

    :param file: DFUFile instance representing the file to be modified.
    :return: 0 on success, -1 on error.
    """

    try:
        _logger.info("Remove TI Stellaris prefix")

        # Get file length
        file.file_p.seek(0, 2)
        length = file.file_p.tell()
        file.file_p.seek(0, 0)

        # Read file content
        data = file.file_p.read()

        # Check if the file has enough data to contain the prefix
        if length < 16:
            _logger.error("Error: File does not contain a valid prefix.")
            return -1

        # Truncate the file
        file.file_p.truncate(0)
        file.file_p.seek(0)

        # Write data without the TI Stellaris prefix
        file.file_p.write(data[16:])

        _logger.info("TI Stellaris prefix removed")
        return 0

    except Exception as e:
        _logger.error(f"Error: {e}")
        return -1


def check_prefix(file: DFUFile) -> int:
    """
    Check if a binary file contains a valid TI Stellaris DFU prefix.

    :param file: DFUFile instance representing the file to be checked.
    :return: 0 if not a valid prefix, 1 if a valid prefix, -1 on error.
    """

    try:
        _logger.info("Check TI Stellaris prefix")

        # Allocate buffer for reading the prefix
        data = bytearray(16)

        # Read prefix from the file
        ret = file.file_p.readinto(data)
        if ret < 16:
            _logger.error("Error: Could not read prefix")
            return -1

        # Check if it's a valid TI Stellaris DFU prefix
        if data[0] != 0x01 or data[1] != 0x00:
            _logger.info("Not a valid TI Stellaris DFU prefix")
            ret = 0
        else:
            _logger.info("Possible TI Stellaris DFU prefix with the following properties:")
            address = 1024 * (data[3] << 8 | data[2])
            payload_length = data[4] | data[5] << 8 | data[6] << 16 | data[7] << 24
            _logger.info(f"Address:        0x{address:08X}")
            _logger.info(f"Payload length: {payload_length}")

        # Rewind the file
        file.file_p.seek(0)

        return ret

    except Exception as e:
        _logger.error(f"Error: {e}")
        return -1

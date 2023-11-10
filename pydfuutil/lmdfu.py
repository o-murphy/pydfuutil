"""
This implements the TI Stellaris DFU
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

as per the Application Update Using the USB Device Firmware Upgrade Class
(Document AN012373)
http://www.ti.com/general/docs/lit/getliterature.tsp?literatureNumber=spma003&fileType=pdf
"""

# lmdfu_dfu_prefix payload length excludes prefix and suffix
lmdfu_dfu_prefix = (
    0x01,  # STELLARIS_DFU_PROG
    0x00,  # Reserved
    0x00,  # LSB start address / 1024
    0x20,  # MSB start address / 1024
    0x00,  # LSB file payload length
    0x00,  # Byte 2 file payload length
    0x00,  # Byte 3 file payload length
    0x00,  # MSB file payload length
)


def lmdfu_add_prefix(file: 'dfu_file.file', address: int):
    """
    TODO: implementation
    :param file:
    :param address:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def lmdfu_remove_prefix(file: 'dfu_file.file'):
    """
    TODO: implementation
    :param file:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def lmdfu_check_prefix(file: 'dfu_file.file'):
    """
    TODO: implementation
    :param file:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

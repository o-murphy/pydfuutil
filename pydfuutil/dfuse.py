"""
This implements the ST Microsystems DFU extensions (DfuSe)
as per the DfuSe 1.1a specification (Document UM0391)
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

from enum import Enum

from pydfuutil.dfu import DFU_IF, dfu_init


DFU_TIMEOUT = 5000
dfu_init(DFU_TIMEOUT)


class DFUSE_COMMAND(Enum):
    SET_ADDRESS = 0x1
    ERASE_PAGE = 0x2
    MASS_ERASE = 0x3
    READ_UNPROTECT = 0x4


def dfuse_special_command(dif: DFU_IF, address: int, command: DFUSE_COMMAND) -> int:
    """
    TODO: implementation
    :param dif:
    :param address:
    :param command:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def dfuse_do_upload(dif: DFU_IF, xfer_size: int, file: 'dfu_file.file', dfuse_options: [str, bytes]) -> int:
    """
    TODO: implementation
    :param dif:
    :param xfer_size:
    :param file:
    :param dfuse_options:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def dfuse_do_dnload(dif: DFU_IF, xfer_size: int, file: 'dfu_file.file', dfuse_options: [str, bytes]) -> int:
    """
    TODO: implementation
    :param dif:
    :param xfer_size:
    :param file:
    :param dfuse_options:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

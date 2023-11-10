"""
Helper functions for reading the memory map in a device
following the ST DfuSe 1.1a specification.
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

from enum import IntFlag

from construct import Struct, Int


class DFUSE(IntFlag):
    DFUSE_READABLE = 0x1
    DFUSE_ERASABLE = 0x2
    DFUSE_WRITEABLE = 0x4


memsegment = Struct(
    start=Int,
    end=Int,
    pagesize=Int,
    memtype=Int,
)


def add_segment(elements: list[memsegment], new_element: memsegment) -> int:
    """
    TODO: implementation
    :param elements:
    :param new_element:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def find_segment(elements: list[memsegment], new_element: memsegment) -> memsegment:
    """
    TODO: implementation
    :param elements:
    :param new_element:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def free_segment_list(elements: list[memsegment]) -> None:
    """
    TODO: implementation
    :param elements:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def parse_memory_layout(intf_desc_str: [str, bytes]) -> memsegment:
    """
    TODO: implementation
    :param intf_desc_str:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

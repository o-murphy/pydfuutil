"""
Helper functions for reading the memory map in a device
following the ST DfuSe 1.1a specification.
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
from dataclasses import dataclass, field
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


@dataclass
class MemSegment:
    start: int
    end: int
    pagesize: int
    memtype: int
    next: 'MemSegment' = field(default=None)

    def __bytes__(self):
        return memsegment.build(self.__dict__)


def add_segment(segment_list: list[MemSegment], segment: MemSegment) -> int:
    """
    TODO: implementation
    :param elements:
    :param new_element:
    :return:
    """
    # raise NotImplementedError("Feature not yet implemented")
    new_element = MemSegment(segment.start, segment.end, segment.pagesize, segment.memtype)

    if not segment_list:
        # list can be empty on the first call
        segment_list.append(new_element)
    else:
        # find the last element in the list
        next_element = segment_list[0]
        while next_element.next:
            next_element = next_element.next
        next_element.next = new_element

    return 0


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

"""
Helper functions for reading the memory map in a device
following the ST DfuSe 1.1a specification.
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import re
from dataclasses import dataclass, field
from enum import IntFlag

from construct import Struct, Int

from pydfuutil.logger import get_logger

logger = get_logger("dfuse_mem")


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
    Find a memory segment in the list containing the given element.

    :param elements: List of MemSegment instances.
    :param new_element: MemSegment instance to search for in the list.
    :return: MemSegment instance if found, None otherwise.
    """
    for element in elements:
        if element.start == new_element.start and element.end == new_element.end:
            return element
    return None


def free_segment_list(elements: list[memsegment]) -> None:
    """
    Free the memory allocated for the list of memory segments.

    :param elements: List of MemSegment instances.
    """
    del elements[:]


# * Parse memory map from interface descriptor string
# * encoded as per ST document UM0424 section 4.3.2.

def parse_memory_layout(intf_desc: [str, bytes], verbose: bool = False) -> memsegment:
    """
    * Parse memory map from interface descriptor string
    * encoded as per ST document UM0424 section 4.3.2.
    :param intf_desc_str:
    :return:
    """

    segment_list = []
    count = 0

    while intf_desc:
        # Read name
        match = re.match(r"^([^/]+)/", intf_desc)
        if match is None:
            logger.error("Error: Could not read name.")
            return None

        name = match.group(1)
        intf_desc = intf_desc[match.end():]

        if verbose:
            logger.info(f"DfuSe interface name: \"{name}\"")

        # Read address
        match = re.match(r"^0x([\da-fA-F]+)/", intf_desc)
        if match is None:
            logger.error("Error: Could not read address.")
            return None

        address = int(match.group(1), 16)
        intf_desc = intf_desc[match.end():]

        while True:
            # Initialize variables
            sectors = 0
            size = 0

            # Read segment details
            match = re.match(r"^(\d+)\*(\d+)([a-zA-Z])?([^/,]+)/", intf_desc)
            if match is None:
                break

            intf_desc = intf_desc[match.end():]
            count += 1

            if match.group(3):
                memtype = ord(match.group(3))
            elif match.group(4) and len(match.group(4)) == 1 and match.group(4) != '/':
                memtype = ord(match.group(4))
            else:
                logger.warning(f"Parsing type identifier '{match.group(4)}' failed for segment {count}")
                continue

            size_multiplier = match.group(3) if match.group(3) else 'B'

            if size_multiplier == 'K':
                size *= 1024
            elif size_multiplier == 'M':
                size *= 1024 * 1024
            elif size_multiplier in {'a', 'b', 'c', 'd', 'e', 'f', 'g'}:
                if not memtype:
                    logger.warning(f"Non-valid multiplier '{size_multiplier}', interpreted as type identifier instead")
                    memtype = size_multiplier

            if not memtype:
                logger.warning(f"No valid type for segment {count}")
                continue

            segment = MemSegment(start=address, end=address + sectors * size - 1, pagesize=size, memtype=memtype & 7)
            segment_list.append(segment)

            if verbose:
                logger.info(f"Memory segment at 0x{address:08x} {sectors} x {size} = {sectors * size} "
                            f"({'r' if memtype & DFUSE.DFUSE_READABLE else ''}"
                            f"{'e' if memtype & DFUSE.DFUSE_ERASABLE else ''}"
                            f"{'w' if memtype & DFUSE.DFUSE_WRITEABLE else ''})")

            address += sectors * size

            separator = intf_desc[0]
            if separator == ',':
                intf_desc = intf_desc[1:]
            else:
                break

    return segment_list

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
logger.warning("Module pydfuutil.dfuse_mem aren't work as expected, "
               "will reimplemented in future")

class DFUSE(IntFlag):
    """DFUSE read/write flags"""
    READABLE = 0x1
    ERASABLE = 0x2
    WRITEABLE = 0x4


memsegment = Struct(
    start=Int,
    end=Int,
    pagesize=Int,
    memtype=Int,
)


@dataclass
class MemSegment:
    """Memory segment"""

    start: int = 0
    end: int = 0
    pagesize: int = 0
    memtype: int = 0
    next: 'MemSegment' = field(default=None)

    def __bytes__(self):
        return memsegment.build(self.__dict__)



def add_segment(seqment_sequence: [MemSegment, None], segment: MemSegment) -> MemSegment:
    """
    :param segment_list:
    :param segment:
    :return: 0 if ok
    """
    new_element = MemSegment(segment.start, segment.end, segment.pagesize, segment.memtype)

    if not seqment_sequence:
        # list can be empty on the first call
        return new_element
    else:
        # find the last element in the list
        next_element = seqment_sequence
        while next_element.next:
            next_element = next_element.next
        next_element.next = new_element

        return seqment_sequence


def find_segment(segment_sequence: MemSegment, new_element: MemSegment) -> [MemSegment, None]:
    """
    Find a memory segment in the list containing the given element.

    :param segment_sequence: List of MemSegment instances.
    :param new_element: MemSegment instance to search for in the list.
    :return: MemSegment instance if found, None otherwise.
    """
    while segment_sequence:
        if segment_sequence.start == new_element.start and segment_sequence.end == new_element.end:
            return segment_sequence
        segment_sequence = segment_sequence.next
    return None


def free_segment_list(segment_sequence: MemSegment) -> None:
    """
    Free the memory allocated for the list of memory segments.

    :param elements: List of MemSegment instances.
    """
    del segment_sequence


# Parse memory map from interface descriptor string
# encoded as per ST document UM0424 section 4.3.2.

def parse_memory_layout(intf_desc: [str, bytes], verbose: bool = False) -> MemSegment:
    """
    Parse memory map from interface descriptor string
    encoded as per ST document UM0424 section 4.3.2.
    :param intf_desc:
    :param verbose:
    :return: MemSegment instance
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
            sectors, size = 0, 0

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
                logger.warning(f"Parsing type identifier '{match.group(4)}' "
                               f"failed for segment {count}")
                continue

            size_multiplier = match.group(3) if match.group(3) else 'B'

            if size_multiplier == 'K':
                size *= 1024
            elif size_multiplier == 'M':
                size *= 1024 * 1024
            elif size_multiplier in {'a', 'b', 'c', 'd', 'e', 'f', 'g'}:
                if not memtype:
                    logger.warning(f"Non-valid multiplier '{size_multiplier}', "
                                   f"interpreted as type identifier instead")
                    memtype = size_multiplier

            if not memtype:
                logger.warning(f"No valid type for segment {count}")
                continue

            segment_list.append(
                MemSegment(
                    start=address,
                    end=address + sectors * size - 1,
                    pagesize=size,
                    memtype=memtype & 7
                )
            )

            if verbose:
                logger.info(f"Memory segment at "
                            f"0x{address:08x} {sectors} x {size} = {sectors * size} "
                            f"({'r' if memtype & DFUSE.READABLE else ''}"
                            f"{'e' if memtype & DFUSE.ERASABLE else ''}"
                            f"{'w' if memtype & DFUSE.WRITEABLE else ''})")

            address += sectors * size

            separator = intf_desc[0]
            if separator == ',':
                intf_desc = intf_desc[1:]
            else:
                break

    return segment_list

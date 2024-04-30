"""
Helper functions for reading the memory map in a device
following the ST DfuSe 1.1a specification.
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""
import logging
import re
from dataclasses import dataclass, field
from enum import IntFlag
from typing import Iterator

from pydfuutil.logger import get_logger

logger = get_logger("dfuse_mem")
logger.warning("Module pydfuutil.dfuse_mem aren't work as expected, "
               "will reimplemented in future")


class DFUSE(IntFlag):
    """DFUSE read/write flags"""
    READABLE = 0x1
    ERASABLE = 0x2
    WRITEABLE = 0x4


@dataclass
class MemSegment:
    """Memory segment"""

    start: int = 0
    end: int = 0
    pagesize: int = 0
    memtype: int = 0
    next: 'MemSegment' = field(default=None)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MemSegment':
        return cls(
            *data[:4],
            next=MemSegment.from_bytes(data[4:])
            if len(data) > 4 else None
        )

    def __iter__(self) -> Iterator['MemSegment']:
        current = self
        while current is not None:
            yield current
            current = current.next

    def __next__(self):
        if self.next is not None:
            return self.next
        raise StopIteration

    def __len__(self):
        ret = 1
        if self.next is not None:
            ret += self.next.__len__()
        return ret

    def __bytes__(self) -> bytes:
        data = bytes((
            self.start,
            self.end,
            self.pagesize,
            self.memtype
        ))
        if self.next:
            data += self.next.__bytes__()
        return data

    def append(self, other: 'MemSegment') -> int:
        if not self.next:
            self.next = other
        else:
            self.next.append(other)
        return 0

    def find(self, address: int) -> ['MemSegment', None]:
        if self.start <= address <= self.end:
            return self
        if self.next is not None:
            return self.next.find(address)
        return None

    def free(self) -> None:
        raise NotImplementedError("Use `del MemSegment()` to free resources")


def add_segment(seqment_sequence: [MemSegment, None], segment: MemSegment) -> MemSegment:
    """
    :param seqment_sequence:
    :param segment:
    :return: 0 if ok
    """
    new_element = MemSegment(segment.start, segment.end, segment.pagesize, segment.memtype)

    if not seqment_sequence:
        # list can be empty on the first call
        return new_element

    # find the last element in the list
    seqment_sequence.append(new_element)
    return seqment_sequence


def find_segment(segment_sequence: MemSegment, address: int) -> [MemSegment, None]:
    """
    Find a memory segment in the list containing the given element.

    :param segment_sequence: List of MemSegment instances.
    :param new_element: MemSegment instance to search for in the list.
    :return: MemSegment instance if found, None otherwise.
    """
    return segment_sequence.find(address)


def free_segment_list(segment_sequence: MemSegment) -> None:
    """
    Free the memory allocated for the list of memory segments.

    :param elements: List of MemSegment instances.
    """
    del segment_sequence


# Parse memory map from interface descriptor string
# encoded as per ST document UM0424 section 4.3.2.

def parse_memory_layout(intf_desc: [str, bytes], verbose: bool = False) -> [MemSegment, None]:
    """
    Parse memory map from interface descriptor string
    encoded as per ST document UM0424 section 4.3.2.
    :param intf_desc:
    :param verbose:
    :return: MemSegment instance
    """

    if verbose:
        logger.setLevel(logging.DEBUG)

    if isinstance(intf_desc, bytes):
        intf_desc = intf_desc.decode('ascii')

    segment_list: [MemSegment, None] = None
    count = 0

    while intf_desc:
        # Read name
        match = re.match(r"^([^/]+)/", intf_desc)
        if match is None:
            print(intf_desc)
            logger.error("Error: Could not read name.")
            return None

        name = match.group(1)
        intf_desc = intf_desc[match.end():]

        logger.debug(f"DfuSe interface name: \"{name}\"")

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

            segment_list = add_segment(segment_list, MemSegment(
                start=address,
                end=address + sectors * size - 1,
                pagesize=size,
                memtype=memtype & 7
            ))

            if verbose:
                logger.debug(f"Memory segment at "
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

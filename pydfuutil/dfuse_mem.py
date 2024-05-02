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

from pydfuutil.logger import logger

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


class DFUSE(IntFlag):
    """DFUSE read/write flags"""
    READABLE = 0x1
    ERASABLE = 0x2
    WRITEABLE = 0x4


@dataclass
class MemSegment:
    """
    Memory segment

    We're using `segment_stack`
    instead of `segment_list`
    to prevent misunderstanding
    with python's `list` type
    """

    start: int = 0
    end: int = 0
    pagesize: int = 0
    mem_type: int = 0
    next: 'MemSegment' = field(default=None)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MemSegment':
        """
        Create a MemSegment stack from binary data
        :param data:
        :return MemSegment:
        """
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
            self.mem_type
        ))
        if self.next:
            data += self.next.__bytes__()
        return data

    def append(self, segment: 'MemSegment') -> None:
        """
        Append the other segment to the stack
        :param segment: MemSegment
        """
        new_segment = MemSegment(
            segment.start,
            segment.end,
            segment.pagesize,
            segment.mem_type
        )
        if not self.next:
            self.next = new_segment
        else:
            self.next.append(new_segment)

    def find(self, address: int) -> ['MemSegment', None]:
        """
        Find a memory segment in the stack containing the given element.
        :param address: MemSegment address for in the stack.
        """
        if self.start <= address <= self.end:
            return self
        if self.next is not None:
            return self.next.find(address)
        return None

    # def free(self) -> None:
    #     """Useless cause of garbage collector"""
    #     raise NotImplementedError("Useless cause of garbage collector")


def add_segment(segment_stack: [MemSegment, None], segment: MemSegment) -> MemSegment:
    """
    :param segment_stack:
    :param segment:
    :return: 0 if ok
    """
    new_element = MemSegment(segment.start, segment.end, segment.pagesize, segment.mem_type)

    if not segment_stack:
        # stack can be empty on the first call
        return new_element

    # find the last element in the stack
    segment_stack.append(new_element)
    return segment_stack


def find_segment(segment_stack: [MemSegment, None], address: int) -> [MemSegment, None]:
    """
    Find a memory segment in the stack containing the given element.

    :param segment_stack: List of MemSegment instances.
    :param address: MemSegment address for in the stack.
    :return: MemSegment instance if found, None otherwise.
    """
    if not segment_stack:
        return None
    return segment_stack.find(address)


# def free_segment_list(segment_stack: MemSegment) -> None:
#     """Useless cause of garbage collector"""
#     raise NotImplementedError("Useless cause of garbage collector")


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

    _logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if isinstance(intf_desc, bytes):
        intf_desc = intf_desc.decode('ascii')

    count: int = 0
    segment_stack: [MemSegment, None] = None
    address: [int, None] = None

    match = re.match(r'@([^/]+)', intf_desc)
    if match is None:
        _logger.error(f"Could not read name, name={match}")
        return None
    name = match.group(1)
    _logger.info(f"DfuSe interface name: {name}")

    intf_desc = intf_desc[match.end():]

    # while per segment
    while (match := re.match(r'/0x(\d+)/', intf_desc)) is not None:
        address = int(match.group(1), 16)

        intf_desc = intf_desc[match.end():]

        # while per address
        while (match := re.match(r'(\d+)\*(\d+)(\w)(\w)[,/]?', intf_desc)) is not None:
            _sectors, _size, multiplier, type_string = match.groups()
            sectors, size = int(_sectors), int(_size)

            _logger.debug(f"{sectors=}, {size=}, {multiplier=}, {type_string=}")

            intf_desc = intf_desc[match.end():]
            count += 1
            mem_type = ord(type_string)

            if multiplier == 'B':
                pass
            elif multiplier == 'K':
                size *= 1024
            elif multiplier == 'M':
                size *= 1024 * 1024
            elif multiplier in ('a', 'b', 'c', 'd', 'e', 'f', 'g'):
                if not mem_type:
                    _logger.warning(f"Non-valid multiplier {multiplier}, "
                                   "interpreted as type identifier instead")
                    mem_type = multiplier

            # fallthrough if mem_type was already set
            else:
                _logger.warning(f"Non-valid multiplier {multiplier} assuming bytes")

            if not mem_type:
                _logger.warning(f"No valid type for segment {count}")

            segment_stack = add_segment(
                segment_stack,
                MemSegment(
                    address,
                    address + sectors * size - 1,
                    size,
                    mem_type & 7
                )
            )

            _logger.debug(f"Memory segment at "
                         f"0x{address:08x} {sectors} x {size} = {sectors * size} "
                         f"({'r' if mem_type & DFUSE.READABLE else ''}"
                         f"{'e' if mem_type & DFUSE.ERASABLE else ''}"
                         f"{'w' if mem_type & DFUSE.WRITEABLE else ''})")

            address += sectors * size

        _logger.debug(f"Parsed details of {count} segments")

    if address is None:
        _logger.error(f"Could not read address, {address=}")

    return segment_stack

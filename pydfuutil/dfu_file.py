"""
Checks for, parses and generates a DFU suffix
Load or store DFU files including suffix and prefix
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import annotations

import errno
import io
import struct
import sys
import warnings
from dataclasses import dataclass, field
from enum import IntEnum

from pydfuutil.exceptions import (
    NoInputError,
    _IOError,
    DataError,
    except_and_safe_exit,
    UsageError,
)
from pydfuutil.logger import logger

_logger = logger.getChild("dfu_file")

DFU_SUFFIX_LENGTH = 16
LMDFU_PREFIX_LENGTH = 8
LPCDFU_PREFIX_LENGTH = 16
STDIN_CHUNK_SIZE = 65536

crc32_table = [
    0x00000000,
    0x77073096,
    0xEE0E612C,
    0x990951BA,
    0x076DC419,
    0x706AF48F,
    0xE963A535,
    0x9E6495A3,
    0x0EDB8832,
    0x79DCB8A4,
    0xE0D5E91E,
    0x97D2D988,
    0x09B64C2B,
    0x7EB17CBD,
    0xE7B82D07,
    0x90BF1D91,
    0x1DB71064,
    0x6AB020F2,
    0xF3B97148,
    0x84BE41DE,
    0x1ADAD47D,
    0x6DDDE4EB,
    0xF4D4B551,
    0x83D385C7,
    0x136C9856,
    0x646BA8C0,
    0xFD62F97A,
    0x8A65C9EC,
    0x14015C4F,
    0x63066CD9,
    0xFA0F3D63,
    0x8D080DF5,
    0x3B6E20C8,
    0x4C69105E,
    0xD56041E4,
    0xA2677172,
    0x3C03E4D1,
    0x4B04D447,
    0xD20D85FD,
    0xA50AB56B,
    0x35B5A8FA,
    0x42B2986C,
    0xDBBBC9D6,
    0xACBCF940,
    0x32D86CE3,
    0x45DF5C75,
    0xDCD60DCF,
    0xABD13D59,
    0x26D930AC,
    0x51DE003A,
    0xC8D75180,
    0xBFD06116,
    0x21B4F4B5,
    0x56B3C423,
    0xCFBA9599,
    0xB8BDA50F,
    0x2802B89E,
    0x5F058808,
    0xC60CD9B2,
    0xB10BE924,
    0x2F6F7C87,
    0x58684C11,
    0xC1611DAB,
    0xB6662D3D,
    0x76DC4190,
    0x01DB7106,
    0x98D220BC,
    0xEFD5102A,
    0x71B18589,
    0x06B6B51F,
    0x9FBFE4A5,
    0xE8B8D433,
    0x7807C9A2,
    0x0F00F934,
    0x9609A88E,
    0xE10E9818,
    0x7F6A0DBB,
    0x086D3D2D,
    0x91646C97,
    0xE6635C01,
    0x6B6B51F4,
    0x1C6C6162,
    0x856530D8,
    0xF262004E,
    0x6C0695ED,
    0x1B01A57B,
    0x8208F4C1,
    0xF50FC457,
    0x65B0D9C6,
    0x12B7E950,
    0x8BBEB8EA,
    0xFCB9887C,
    0x62DD1DDF,
    0x15DA2D49,
    0x8CD37CF3,
    0xFBD44C65,
    0x4DB26158,
    0x3AB551CE,
    0xA3BC0074,
    0xD4BB30E2,
    0x4ADFA541,
    0x3DD895D7,
    0xA4D1C46D,
    0xD3D6F4FB,
    0x4369E96A,
    0x346ED9FC,
    0xAD678846,
    0xDA60B8D0,
    0x44042D73,
    0x33031DE5,
    0xAA0A4C5F,
    0xDD0D7CC9,
    0x5005713C,
    0x270241AA,
    0xBE0B1010,
    0xC90C2086,
    0x5768B525,
    0x206F85B3,
    0xB966D409,
    0xCE61E49F,
    0x5EDEF90E,
    0x29D9C998,
    0xB0D09822,
    0xC7D7A8B4,
    0x59B33D17,
    0x2EB40D81,
    0xB7BD5C3B,
    0xC0BA6CAD,
    0xEDB88320,
    0x9ABFB3B6,
    0x03B6E20C,
    0x74B1D29A,
    0xEAD54739,
    0x9DD277AF,
    0x04DB2615,
    0x73DC1683,
    0xE3630B12,
    0x94643B84,
    0x0D6D6A3E,
    0x7A6A5AA8,
    0xE40ECF0B,
    0x9309FF9D,
    0x0A00AE27,
    0x7D079EB1,
    0xF00F9344,
    0x8708A3D2,
    0x1E01F268,
    0x6906C2FE,
    0xF762575D,
    0x806567CB,
    0x196C3671,
    0x6E6B06E7,
    0xFED41B76,
    0x89D32BE0,
    0x10DA7A5A,
    0x67DD4ACC,
    0xF9B9DF6F,
    0x8EBEEFF9,
    0x17B7BE43,
    0x60B08ED5,
    0xD6D6A3E8,
    0xA1D1937E,
    0x38D8C2C4,
    0x4FDFF252,
    0xD1BB67F1,
    0xA6BC5767,
    0x3FB506DD,
    0x48B2364B,
    0xD80D2BDA,
    0xAF0A1B4C,
    0x36034AF6,
    0x41047A60,
    0xDF60EFC3,
    0xA867DF55,
    0x316E8EEF,
    0x4669BE79,
    0xCB61B38C,
    0xBC66831A,
    0x256FD2A0,
    0x5268E236,
    0xCC0C7795,
    0xBB0B4703,
    0x220216B9,
    0x5505262F,
    0xC5BA3BBE,
    0xB2BD0B28,
    0x2BB45A92,
    0x5CB36A04,
    0xC2D7FFA7,
    0xB5D0CF31,
    0x2CD99E8B,
    0x5BDEAE1D,
    0x9B64C2B0,
    0xEC63F226,
    0x756AA39C,
    0x026D930A,
    0x9C0906A9,
    0xEB0E363F,
    0x72076785,
    0x05005713,
    0x95BF4A82,
    0xE2B87A14,
    0x7BB12BAE,
    0x0CB61B38,
    0x92D28E9B,
    0xE5D5BE0D,
    0x7CDCEFB7,
    0x0BDBDF21,
    0x86D3D2D4,
    0xF1D4E242,
    0x68DDB3F8,
    0x1FDA836E,
    0x81BE16CD,
    0xF6B9265B,
    0x6FB077E1,
    0x18B74777,
    0x88085AE6,
    0xFF0F6A70,
    0x66063BCA,
    0x11010B5C,
    0x8F659EFF,
    0xF862AE69,
    0x616BFFD3,
    0x166CCF45,
    0xA00AE278,
    0xD70DD2EE,
    0x4E048354,
    0x3903B3C2,
    0xA7672661,
    0xD06016F7,
    0x4969474D,
    0x3E6E77DB,
    0xAED16A4A,
    0xD9D65ADC,
    0x40DF0B66,
    0x37D83BF0,
    0xA9BCAE53,
    0xDEBB9EC5,
    0x47B2CF7F,
    0x30B5FFE9,
    0xBDBDF21C,
    0xCABAC28A,
    0x53B39330,
    0x24B4A3A6,
    0xBAD03605,
    0xCDD70693,
    0x54DE5729,
    0x23D967BF,
    0xB3667A2E,
    0xC4614AB8,
    0x5D681B02,
    0x2A6F2B94,
    0xB40BBE37,
    0xC30C8EA1,
    0x5A05DF1B,
    0x2D02EF8D,
]


@dataclass
class DFUFileSize:
    """Dfu file size struct"""

    total: int = 0
    prefix: int = 0
    suffix: int = 0


class SuffixReq(IntEnum):
    """Suffix requirement"""

    NO_SUFFIX = 0
    NEEDS_SUFFIX = 1
    MAYBE_SUFFIX = 2


class PrefixReq(IntEnum):
    """Prefix requirement"""

    NO_PREFIX = 0
    NEEDS_PREFIX = 1
    MAYBE_PREFIX = 2


class PrefixType(IntEnum):
    """Dfu prefix type"""

    ZERO_PREFIX = 0
    LMDFU_PREFIX = 1
    LPCDFU_UNENCRYPTED_PREFIX = 2


@dataclass
class DfuFile:  # pylint: disable=too-many-instance-attributes, invalid-name
    """Class to store DFU file data"""

    name: str | None
    firmware: bytearray | bytes = field(default_factory=bytearray)
    file_p: io.BufferedIOBase | None = None
    size: DFUFileSize = field(default_factory=DFUFileSize)
    lmdfu_address: int = 0
    prefix_type: PrefixType = PrefixType.ZERO_PREFIX
    dwCRC: int = 0
    bcdDFU: int = 0
    idVendor: int = 0xFFFF  # wildcard value
    idProduct: int = 0xFFFF  # wildcard value
    bcdDevice: int = 0xFFFF  # wildcard value

    def dump(self, write_suffix: bool, write_prefix: bool) -> None:
        """writes suffix and/or prefix to dfu file"""
        return _store_file(self, write_suffix, write_prefix)

    def load(self, check_suffix: SuffixReq, check_prefix: PrefixReq) -> None:
        """loads suffix and/or prefix from dfu file"""
        return _load_file(self, check_suffix, check_prefix)

    def write_crc(self, crc: int, buf: bytes | bytearray) -> int:
        """writes desired data to dfu file"""
        assert self.file_p is not None
        return _write_crc(self.file_p, crc, buf)

    def show_suffix_and_prefix(self) -> None:
        """Prints suffix and prefix of dfu file"""
        _show_suffix_and_prefix(self)


def crc32_byte(accum: int, delta: int):
    """Calculate a 32-bit CRC"""
    return crc32_table[(accum ^ delta) & 0xFF] ^ (accum >> 8)


def _probe_prefix(file: DfuFile):
    prefix = file.firmware

    if file.size.total < LMDFU_PREFIX_LENGTH:
        return 1
    if prefix[0] == 0x01 and prefix[1] == 0x00:
        payload_len = (
            (prefix[7] << 24) | (prefix[6] << 16) | (prefix[5] << 8) | prefix[4]
        )
        expected_payload_len = file.size.total - LMDFU_PREFIX_LENGTH - file.size.suffix
        if payload_len != expected_payload_len:
            return 1
        file.prefix_type = PrefixType.LMDFU_PREFIX
        file.size.prefix = LMDFU_PREFIX_LENGTH
        file.lmdfu_address = 1024 * ((prefix[3] << 8) | prefix[2])

    elif ((prefix[0] & 0x3F) == 0x1A) and ((prefix[1] & 0x3F) == 0x3F):
        file.prefix_type = PrefixType.LPCDFU_UNENCRYPTED_PREFIX
        file.size.prefix = LPCDFU_PREFIX_LENGTH
    if file.size.prefix + file.size.suffix > file.size.total:
        return 1
    return 0


def _write_crc(f: io.BufferedIOBase, crc: int, buf: bytes | bytearray) -> int:
    """writes desired data to dfu file"""

    # compute CRC
    size = len(buf)
    for x in range(0, size):
        crc = crc32_byte(crc, buf[x])

    # write data
    if f.write(buf) != size:
        raise _IOError(f"Could not write {size} bytes to {f}")

    return crc


@except_and_safe_exit(_logger)
def _load_file(file: DfuFile, check_suffix: SuffixReq, check_prefix: PrefixReq) -> None:
    """loads suffix and/or prefix from dfu file"""

    file.size.prefix = 0
    file.size.suffix = 0

    file.bcdDFU = 0
    file.idVendor = 0xFFFF
    file.idProduct = 0xFFFF
    file.bcdDevice = 0xFFFF

    file.lmdfu_address = 0
    if file.name == "-":
        file.firmware = bytearray()
        read_bytes = sys.stdin.buffer.read(STDIN_CHUNK_SIZE)
        while read_bytes:
            file.firmware.extend(read_bytes)
            read_bytes = sys.stdin.buffer.read(STDIN_CHUNK_SIZE)
        file.size.total = len(file.firmware)
        _logger.debug(f"Read {file.size.total} bytes from stdin")

        check_suffix = SuffixReq.MAYBE_SUFFIX
    else:
        assert file.name is not None
        try:
            with open(file.name, "rb") as f:
                file.firmware = bytearray(f.read())
                file.size.total = len(file.firmware)
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise NoInputError(
                    f"Could not open file {file.name} for reading"
                ) from e
            if e.errno == errno.EACCES:
                raise _IOError(f"Permission denied: {file.name}") from e
            raise _IOError(f"Error reading file {file.name}: {e}") from e

    missing_suffix, reason = False, None
    if file.size.total < DFU_SUFFIX_LENGTH:
        reason = "File too short for DFU suffix"
        missing_suffix = True
    else:
        dfu_suffix = file.firmware[-DFU_SUFFIX_LENGTH:]
        file.dwCRC = struct.unpack("<I", dfu_suffix[12:])[0]

        crc = 0xFFFFFFFF
        for byte in file.firmware[:-4]:
            crc = crc32_byte(crc, byte)

        if dfu_suffix[8:11] != b"UFD":
            reason = "Invalid DFU suffix signature"
            missing_suffix = True
        elif struct.unpack("<I", dfu_suffix[12:])[0] != crc:
            reason = "DFU suffix CRC does not match"
            missing_suffix = True
        else:
            file.bcdDFU = struct.unpack("<H", dfu_suffix[6:8])[0]
            _logger.debug(f"DFU suffix version {file.bcdDFU}")

            file.size.suffix = dfu_suffix[11]
            if file.size.suffix < DFU_SUFFIX_LENGTH:
                raise DataError(f"Unsupported DFU suffix length {file.size.suffix}")
            if file.size.suffix > file.size.total:
                raise DataError(f"Invalid DFU suffix length {file.size.suffix}")

            file.idVendor = struct.unpack("<H", dfu_suffix[4:6])[0]
            file.idProduct = struct.unpack("<H", dfu_suffix[2:4])[0]
            file.bcdDevice = struct.unpack("<H", dfu_suffix[0:2])[0]

    if missing_suffix:
        assert reason is not None
        if check_suffix == SuffixReq.NEEDS_SUFFIX:
            raise DataError(reason + " Valid DFU suffix needed")
        if check_suffix == SuffixReq.MAYBE_SUFFIX:
            _logger.warning(f"{reason}")
            warnings.warn(
                "A valid DFU suffix will be required in a future dfu-util release",
                FutureWarning,
            )
    else:
        if check_suffix == SuffixReq.NO_SUFFIX:
            raise DataError(
                "Please remove existing DFU suffix before adding a new one."
            )

    res = _probe_prefix(file)
    if (res or file.size.prefix == 0) and check_prefix == PrefixReq.NEEDS_PREFIX:
        raise UsageError("Valid DFU prefix needed")
    if file.size.prefix and check_prefix == PrefixReq.NO_PREFIX:
        raise DataError("A prefix already exists, please delete it first")
    if file.size.prefix:
        data = file.firmware
        if file.prefix_type == PrefixType.LMDFU_PREFIX:
            _logger.debug(
                f"Possible TI Stellaris DFU prefix with the following properties\n"
                f"Address:        0x{file.lmdfu_address:08x}\n"
                f"Payload length: {struct.unpack('<I', data[4:8])[0]}"
            )
        elif file.prefix_type == PrefixType.LPCDFU_UNENCRYPTED_PREFIX:
            _logger.debug(
                f"Possible unencrypted NXP LPC DFU prefix with the following properties\n"
                f"Payload length: {struct.unpack('<H', data[2:4])[0] >> 1} kiByte"
            )
        else:
            raise DataError("Unknown DFU prefix type")


@except_and_safe_exit(_logger)
def _store_file(file: DfuFile, write_suffix: bool, write_prefix: bool) -> None:
    """writes suffix and/or prefix to dfu file"""

    crc = 0xFFFFFFFF

    assert file.name is not None
    try:
        with open(file.name, "wb") as file.file_p:
            # Write prefix, if any
            if write_prefix:
                if file.prefix_type == PrefixType.LMDFU_PREFIX:
                    addr = file.lmdfu_address // 1024
                    len_payload = file.size.total - file.size.prefix - file.size.suffix

                    lmdfu_prefix = bytearray(LMDFU_PREFIX_LENGTH)
                    lmdfu_prefix[0] = 0x01  # STELLARIS_DFU_PROG
                    lmdfu_prefix[2:4] = addr.to_bytes(2, "little")
                    lmdfu_prefix[4:8] = len_payload.to_bytes(4, "little")

                    crc = _write_crc(file.file_p, crc, lmdfu_prefix)

                elif file.prefix_type == PrefixType.LPCDFU_UNENCRYPTED_PREFIX:
                    len_payload = (file.size.total - file.size.suffix + 511) // 512

                    lpc_dfu_prefix = bytearray(LPCDFU_PREFIX_LENGTH)
                    lpc_dfu_prefix[0] = 0x1A  # Unencrypted
                    lpc_dfu_prefix[1] = 0x3F  # Reserved
                    lpc_dfu_prefix[2:4] = len_payload.to_bytes(2, "little")

                    for i in range(12, LPCDFU_PREFIX_LENGTH):
                        lpc_dfu_prefix[i] = 0xFF

                    crc = _write_crc(file.file_p, crc, lpc_dfu_prefix)

            # Write firmware binary
            crc = _write_crc(
                file.file_p,
                crc,
                file.firmware[file.size.prefix : file.size.total - file.size.suffix],
            )

            # Write suffix, if any
            if write_suffix:
                dfu_suffix = bytearray(16)
                dfu_suffix[0:2] = file.bcdDevice.to_bytes(2, "little")
                dfu_suffix[2:4] = file.idProduct.to_bytes(2, "little")
                dfu_suffix[4:6] = file.idVendor.to_bytes(2, "little")
                dfu_suffix[6:8] = file.bcdDFU.to_bytes(2, "little")
                dfu_suffix[8:11] = b"UFD"
                dfu_suffix[11] = DFU_SUFFIX_LENGTH

                crc = file.write_crc(crc, dfu_suffix[:-4])

                dfu_suffix[12:16] = crc.to_bytes(4, "little")
                _write_crc(file.file_p, crc, dfu_suffix[12:])

    except IOError as e:
        if e.errno == errno.ENOENT:
            raise _IOError(f"Could not open file {file.name} for writing") from e
        if e.errno == errno.EACCES:
            raise _IOError(f"Permission denied: {file.name}") from e
        raise _IOError(f"Error opening file {file.name}: {e}") from e


def _show_suffix_and_prefix(file: DfuFile) -> None:
    """Prints suffix and prefix of dfu file"""

    if file.size.prefix == LMDFU_PREFIX_LENGTH:
        print(
            f"The file {file.name} contains a TI Stellaris "
            f"DFU prefix with the following properties:"
        )
        print(f"Address:\t0x{file.lmdfu_address:08x}")
    elif file.size.prefix == LPCDFU_PREFIX_LENGTH:
        prefix = file.firmware
        size_kib = prefix[2] >> 1 | prefix[3] << 7
        print(
            f"The file {file.name} contains a NXP unencrypted "
            f"LPC DFU prefix with the following properties:"
        )
        print(f"Size:\t{size_kib:5} kiB")
    elif file.size.prefix != 0:
        print(f"The file {file.name} contains an unknown prefix")

    if file.size.suffix > 0:
        print(
            f"The file {file.name} contains a DFU suffix with the following properties:"
        )
        print(f"BCD device:\t0x{file.bcdDevice:04X}")
        print(f"Product ID:\t0x{file.idProduct:04X}")
        print(f"Vendor ID:\t0x{file.idVendor:04X}")
        print(f"BCD DFU:\t0x{file.bcdDFU:04X}")
        print(f"Length:\t\t{file.size.suffix}")
        print(f"CRC:\t\t0x{file.dwCRC:08X}")


__all__ = (
    "DfuFile",
    "SuffixReq",
    "PrefixReq",
    "PrefixType",
)

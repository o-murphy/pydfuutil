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

import io
import os
import struct
import sys
import warnings
from dataclasses import dataclass, field
from enum import Enum

from construct import (Struct, Const, ByteSwapped, Default,
                       Int32ub, Int16ub, Int8sb,
                       ConstError, StreamError)

from pydfuutil.logger import logger

__all__ = ('DFUFile', 'parse_dfu_suffix', 'generate_dfu_suffix')

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

DFU_SUFFIX_LENGTH = 16
LMDFU_PREFIX_LENGTH = 8
LPCDFU_PREFIX_LENGTH = 16
STDIN_CHUNK_SIZE = 65536

crc32_table = [
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
    0xe963a535, 0x9e6495a3, 0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
    0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
    0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
    0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9,
    0xfa0f3d63, 0x8d080df5, 0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
    0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b, 0x35b5a8fa, 0x42b2986c,
    0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
    0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
    0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
    0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d, 0x76dc4190, 0x01db7106,
    0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
    0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
    0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
    0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
    0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
    0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
    0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
    0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
    0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
    0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
    0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
    0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
    0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
    0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
    0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
    0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
    0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
    0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
    0x316e8eef, 0x4669be79, 0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
    0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
    0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
    0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
    0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
    0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
    0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
    0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
    0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
    0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
    0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
    0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
    0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
    0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
]

_suffix = ByteSwapped(Struct(
    dwCRC=Default(Int32ub, 0xffffffff),
    bLength=Const(DFU_SUFFIX_LENGTH, Int8sb),
    ucDfuSignature=Const(b'DFU'),
    bcdDFU=Int16ub,
    idVendor=Int16ub,
    idProduct=Int16ub,
    bcdDevice=Int16ub,
))


@dataclass
class DFUFile:  # pylint: disable=too-many-instance-attributes, invalid-name
    """Class to store DFU file data"""
    name: [str, None]
    file_p: io.FileIO = None
    size: int = 0
    dwCRC: int = 0
    suffix_len: int = 0
    bcdDFU: int = 0
    idVendor: int = 0xffff  # wildcard value
    idProduct: int = 0xffff  # wildcard value
    bcdDevice: int = 0xffff  # wildcard value

    def parse_dfu_suffix(self) -> int:
        """Bind parse_dfu_suffix to DFUFile instance"""
        return parse_dfu_suffix(self)

    def generate_dfu_suffix(self) -> int:
        """Bind generate_dfu_suffix to DFUFile instance"""
        return generate_dfu_suffix(self)


@dataclass
class DFUFileSize:
    total: int
    prefix: int
    suffix: int


class SuffixReq(Enum):
    NO_SUFFIX = 0
    NEEDS_SUFFIX = 1
    MAYBE_SUFFIX = 2


class PrefixReq(Enum):
    NO_SUFFIX = 0
    NEEDS_SUFFIX = 1
    MAYBE_SUFFIX = 2


class PrefixType(Enum):
    ZERO_PREFIX = 0
    LMDFU_PREFIX = 1
    LPCDFU_UNENCRYPTED_PREFIX = 2


@dataclass
class DFUFile011:  # pylint: disable=too-many-instance-attributes, invalid-name
    """Class to store DFU file data"""
    name: [str, None]
    firmware: [bytearray, bytes] = field(default_factory=bytearray)
    file_p: io.FileIO = None
    size: DFUFileSize = None
    lmdfu_address: int = 0
    prefix_type: PrefixType = None
    dwCRC: int = 0
    bcdDFU: int = 0
    idVendor: int = 0xffff  # wildcard value
    idProduct: int = 0xffff  # wildcard value
    bcdDevice: int = 0xffff  # wildcard value

    def parse_dfu_suffix(self) -> int:
        """Bind parse_dfu_suffix to DFUFile instance"""
        return parse_dfu_suffix(self)

    def generate_dfu_suffix(self) -> int:
        """Bind generate_dfu_suffix to DFUFile instance"""
        return generate_dfu_suffix(self)


def crc32_byte(accum: int, delta: int):
    """
    Calculate a 32-bit CRC
    """
    return crc32_table[(accum ^ delta) & 0xff] ^ (accum >> 8)


def probe_prefix(file: DFUFile011):
    prefix = file.firmware

    if file.size.total < LMDFU_PREFIX_LENGTH:
        return 1
    if prefix[0] == 0x01 and prefix[1] == 0x00:
        payload_len = ((prefix[7] << 24) | (prefix[6] << 16)
                       | (prefix[5] << 8) | prefix[4])
        expected_payload_len = file.size.total - LMDFU_PREFIX_LENGTH - file.size.suffix
        if payload_len != expected_payload_len:
            return 1
        file.prefix_type = PrefixType.LMDFU_PREFIX
        file.size.prefix = LMDFU_PREFIX_LENGTH
        file.lmdfu_address = 1024 * ((prefix[3] << 8) | prefix[2])

    elif ((prefix[0] & 0x3f) == 0x1a) and ((prefix[1] & 0x3f) == 0x3f):
        file.prefix_type = PrefixType.LPCDFU_UNENCRYPTED_PREFIX
        file.size.prefix = LPCDFU_PREFIX_LENGTH
    if file.size.prefix + file.size.suffix > file.size.total:
        return 1
    return 0


def write_crc(f: DFUFile.file_p, crc: int, buf: [bytes, bytearray], size: int) -> int:
    # compute CRC
    for x in range(0, size):
        crc = crc32_byte(crc, buf[x])

    # write data
    if f.write(buf, size) != size:
        _logger.error(f"Could not write {size} bytes to {f}")

    return crc


def load_file(file: DFUFile011, check_suffix: SuffixReq, check_prefix: PrefixReq):

    file.size.prefix = 0
    file.size.suffix = 0

    # default values, if no valid suffix is found
    file.bcdDFU = 0
    file.idVendor = 0xffff  # wildcard value
    file.idProduct = 0xffff  # wildcard value
    file.bcdDevice = 0xffff  # wildcard value

    # default values, if no valid prefix is found
    file.lmdfu_address = 0

    file.firmware = None

    if file.name and file.name != '-':

        if sys.stdin.isatty():
            print("Please provide input via stdin.")
            return None

        # Check if the platform is Windows
        if sys.platform.startswith("win"):
            import msvcrt
            # Set stdin to binary mode
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

        file.firmware = bytearray()
        read_bytes = sys.stdin.buffer.read(STDIN_CHUNK_SIZE)
        file.firmware += read_bytes
        file.size.total = len(read_bytes)

        while len(read_bytes) == STDIN_CHUNK_SIZE:
            read_bytes = sys.stdin.buffer.read(STDIN_CHUNK_SIZE)
            file.firmware += read_bytes
            file.size.total += len(read_bytes)

        _logger.debug(f"Read {file.size.total} bytes from stdin")

        # Never require suffix when reading from stdin
        check_suffix = SuffixReq.MAYBE_SUFFIX
    else:
        with open(file.name, 'rb') as file.file_p:
            file.firmware = file.file_p.read()
            file.size.total = len(file.firmware)

    # TODO
    raise NotImplementedError
    # # Check for possible DFU file suffix by trying to parse one
    # if check_suffix != SuffixReq.NO_SUFFIX:
    #     dfusuffix = file.firmware[-16:] if file.size['total'] >= 16 else None
    #     missing_suffix = False
    #     reason = None
    #
    #     if not dfusuffix:
    #         reason = "File too short for DFU suffix"
    #         missing_suffix = True
    #     elif dfusuffix[10:13] != b'DFU':
    #         reason = "Invalid DFU suffix signature"
    #         missing_suffix = True
    #     else:
    #         crc = 0xffffffff
    #         for byte in file.firmware[:-16]:
    #             crc = crc32_byte(crc, byte)
    #
    #         file.dwCRC = struct.unpack('<I', dfusuffix[12:16])[0]
    #         if file.dwCRC != crc:
    #             reason = "DFU suffix CRC does not match"
    #             missing_suffix = True
    #         else:
    #             file.bcdDFU = struct.unpack('<H', dfusuffix[6:8])[0]
    #             _logger.debug(f"DFU suffix version {file.bcdDFU}")
    #
    #             file.size.suffix = dfusuffix[11]
    #             if file.size.suffix < 16:
    #                 raise ValueError("Unsupported DFU suffix length")
    #             if file.size.suffix > file.size.total:
    #                 raise ValueError("Invalid DFU suffix length")
    #
    #             file.idVendor = struct.unpack('<H', dfusuffix[4:6])[0]
    #             file.idProduct = struct.unpack('<H', dfusuffix[2:4])[0]
    #             file.bcdDevice = struct.unpack('<H', dfusuffix[0:2])[0]
    #
    #     if missing_suffix:
    #         if check_suffix == SuffixReq.NEEDS_SUFFIX:
    #             _logger.info(f"{reason}")
    #             _logger.info("A valid DFU suffix will be required in a future dfu-util release")
    #             # raise ValueError("Valid DFU suffix needed")
    #
    #     elif check_suffix == SuffixReq.MAYBE_SUFFIX:
    #         _logger.warning(f"{reason}")


def store_file(file: DFUFile011, write_suffix: int, write_prefix: int):
    crc = 0xffffffff

    try:
        with open(file.name, 'wb') as file.file_p:

            # write prefix, if any
            if write_prefix:
                if file.prefix_type == PrefixType.LMDFU_PREFIX:
                    lmdfu_prefix = bytearray(LMDFU_PREFIX_LENGTH)
                    addr = file.lmdfu_address // 1024

                    # lmdfu_dfu_prefix payload length excludes prefix and suffix
                    len_ = file.size.total - file.size.prefix - file.size.suffix

                    lmdfu_prefix[0] = 0x01  # STELLARIS_DFU_PROG
                    lmdfu_prefix[1] = 0x00  # Reserved
                    lmdfu_prefix[2] = addr & 0xff
                    lmdfu_prefix[3] = addr >> 8
                    lmdfu_prefix[4] = len_ & 0xff
                    lmdfu_prefix[5] = (len_ >> 8) & 0xff
                    lmdfu_prefix[6] = (len_ >> 16) & 0xff
                    lmdfu_prefix[7] = (len_ >> 24)

                    crc = write_crc(file.file_p, crc, lmdfu_prefix, LMDFU_PREFIX_LENGTH)

                if file.prefix_type == PrefixType.LPCDFU_UNENCRYPTED_PREFIX:
                    lpcdfu_prefix = bytearray(LPCDFU_PREFIX_LENGTH)

                    # Payload is firmware and prefix rounded to 512 bytes
                    len_ = (file.size.total - file.size.suffix + 511) // 512

                    lpcdfu_prefix[0] = 0x1a  # Unencypted
                    lpcdfu_prefix[1] = 0x3f  # Reserved
                    lpcdfu_prefix[2] = (len_ & 0xff)
                    lpcdfu_prefix[3] = (len_ >> 8) & 0xff
                    for i in range(12, LPCDFU_PREFIX_LENGTH):
                        lpcdfu_prefix[i] = 0xff

                    crc = write_crc(file.file_p, crc, lpcdfu_prefix, LPCDFU_PREFIX_LENGTH)

            # write firmware binary
            crc = write_crc(file.file_p, crc, file.firmware[file.size.prefix:],
                            file.size.total + file.size.prefix + file.size.suffix)

            # write suffix, if any
            if write_suffix:
                dfusuffix = bytearray(DFU_SUFFIX_LENGTH)

                dfusuffix[0] = file.bcdDevice & 0xff
                dfusuffix[1] = file.bcdDevice >> 8
                dfusuffix[2] = file.idProduct & 0xff
                dfusuffix[3] = file.idProduct >> 8
                dfusuffix[4] = file.idVendor & 0xff
                dfusuffix[5] = file.idVendor >> 8
                dfusuffix[6] = file.bcdDFU & 0xff
                dfusuffix[7] = file.bcdDFU >> 8
                dfusuffix[8] = ord('U')
                dfusuffix[9] = ord('F')
                dfusuffix[10] = ord('D')
                dfusuffix[11] = DFU_SUFFIX_LENGTH

                crc = write_crc(file.file_p, crc, dfusuffix, DFU_SUFFIX_LENGTH - 4)

                dfusuffix[12] = crc
                dfusuffix[13] = crc >> 8
                dfusuffix[14] = crc >> 16
                dfusuffix[15] = crc >> 24

                crc = write_crc(file.file_p, crc, dfusuffix[12:], 4)

    except OSError as err:
        _logger.debug(err)
        raise OSError(f"Could not open file {file.name} for writing")


def show_suffix_and_prefix(file: DFUFile011) -> None:

    if file.size.prefix == LPCDFU_PREFIX_LENGTH:
        print(f"The file {file.name} contains a TI Stellaris "
              f"DFU prefix with the following properties:")
        print(f"Address:\t0x{file.lmdfu_address:08x}")
    elif file.size.prefix == LPCDFU_PREFIX_LENGTH:
        prefix = file.firmware
        size_kib = prefix[2] >> 1 | prefix[3] << 7
        print(f"The file {file.name} contains a NXP unencrypted "
              f"LPC DFU prefix with the following properties:")
        print(f"Size:\t{size_kib:5} kiB")
    elif file.size.prefix != 0:
        print(f"The file {file.name} contains an unknown prefix")

    if file.size.suffix > 0:
        print(f"The file {file.name} contains a DFU suffix with the following properties:")
        print(f"BCD device:\t0x{file.bcdDevice:04X}")
        print(f"Product ID:\t0x{file.idProduct:04X}")
        print(f"Vendor ID:\t0x{file.idVendor:04X}")
        print(f"BCD DFU:\t0x{file.bcdDFU:04X}")
        print(f"Length:\t\t{file.size.suffix}")
        print(f"CRC:\t\t0x{file.dwCRC:08X}")


def parse_dfu_suffix(file: DFUFile) -> int:
    """
    reads the file_p and name member, fills in all others
    FIXME: deprecated
    :param file:
    :return: 0 if no DFU suffix, positive if valid DFU suffix, negative on file read error
    """
    warnings.warn("parse_dfu_suffix is deprecated", FutureWarning)

    crc = 0xffffffff
    dfu_suffix = bytearray([0] * DFU_SUFFIX_LENGTH)

    try:
        with io.FileIO(file.name, 'rb') as file.file_p:
            file.size = file.file_p.seek(0, os.SEEK_END)
            file.file_p.seek(0)

            if file.size < DFU_SUFFIX_LENGTH:
                _logger.error("File too short for DFU suffix")
                return 0

            firmware = bytearray(file.file_p.read(file.size))

            for i in range(file.size - 4):
                crc = crc32_byte(crc, firmware[i])

            del firmware

            file.file_p.seek(-DFU_SUFFIX_LENGTH, os.SEEK_END)
            ret = file.file_p.readinto(dfu_suffix)

            if ret < 0:
                _logger.error("Could not read DFU suffix")
                return ret
            if ret < DFU_SUFFIX_LENGTH:
                _logger.error("Could not read whole DFU suffix")
                return -1

            suffix = _suffix.parse(dfu_suffix)
            file.dwCRC = suffix.dwCRC

            if file.dwCRC != crc:
                _logger.error("DFU CRC does not match")
                return 0

            file.bcdDFU = suffix.bcdDFU
            _logger.info(f"Dfu suffix version {hex(file.bcdDFU)}")

            file.suffix_len = dfu_suffix[11]
            if file.suffix_len < DFU_SUFFIX_LENGTH:
                _logger.error(f"Unsupported DFU suffix length {file.suffix_len}")
                return 0

            file.idVendor = suffix.idVendor
            file.idProduct = suffix.idProduct
            file.bcdDevice = suffix.bcdDevice

    except StreamError as e:
        _logger.error(f"Could not read whole DFU suffix, {e}")
        ret = -1
    except ConstError as e:
        _logger.error(f"No valid DFU suffix signature, {e}")
        ret = 0
    except Exception as e:
        _logger.exception(e)
        ret = -1
    return ret


def generate_dfu_suffix(file: DFUFile) -> int:
    """
    reads file, generates CRC and adds DFU suffix to file
    :param file:
    :return: positive on success, negative on errors
    """
    warnings.warn("generate_dfu_suffix is deprecated", FutureWarning)

    file.size = 0
    file.dwCRC = 0xffffffff
    file.suffix_len = DFU_SUFFIX_LENGTH
    file.bcdDFU = 0x0100  # Default to bcdDFU version 1.0

    suffix_data = {
        'bcdDevice': file.bcdDevice,
        'idProduct': file.idProduct,
        'idVendor': file.idVendor,
        'bcdDFU': file.bcdDFU,
        'bLength': file.suffix_len
    }

    dfu_suffix = bytearray(_suffix.build(suffix_data))

    try:
        with io.FileIO(file.name, 'rb+') as file_p:
            file.size = file_p.seek(0, os.SEEK_END)
            file_p.seek(0)

            # Make space for all but CRC
            firmware = bytearray(file_p.read(file.size))
            firmware.extend(dfu_suffix[:12])
            # Calculate CRC. It is calculated over file and suffix excluding the CRC itself
            for i in range(file.size + file.suffix_len - 4):
                file.dwCRC = crc32_byte(file.dwCRC, firmware[i])

            del firmware

            dfu_suffix[12:16] = ByteSwapped(_suffix.subcon.dwCRC).build(file.dwCRC)

            # Move to the end of the file
            file_p.seek(0, os.SEEK_END)

            # Add the suffix at the end of the file
            ret = file_p.write(dfu_suffix)

    except Exception as e:
        _logger.exception(e)
        ret = -1

    return ret

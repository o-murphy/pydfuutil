"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import argparse
import importlib.metadata
import os
import sys
from enum import IntEnum

from pydfuutil import __copyright__
# from pydfuutil import lmdfu
from pydfuutil.dfu_file import DFUFile, SuffixReq, PrefixReq
# , parse_dfu_suffix)
from pydfuutil.exceptions import GeneralWarning, GeneralError, MissuseError, handle_exceptions
from pydfuutil.logger import logger

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


class Mode(IntEnum):
    """DFU suffix operate mode"""
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


# class LmdfuMode(IntEnum):
#     """LMDFU suffix operate mode"""
#     NONE = 0x1
#     ADD = 0x2
#     DEL = 0x3
#     CHECK = 0x4


VERSION = (f'pydfuutil-suffix " {__version__} "\n {__copyright__[0]}\n'
           f'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


def check_suffix(file: DFUFile) -> int:
    """check dfu suffix for valid and prints it"""
    ret: int

    ret = parse_dfu_suffix(file)
    if ret > 0:
        print(f"The file {file.name} contains a DFU suffix with the following properties:")
        print(f"BCD device:\t0x{file.bcdDevice:04X}")
        print(f"Product ID:\t0x{file.idProduct:04X}")
        print(f"Vendor ID:\t0x{file.idVendor:04X}")
        print(f"BCD DFU:\t0x{file.bcdDFU:04X}")
        print(f"Length:\t\t{file.suffix_len}")
        print(f"CRC:\t\t0x{file.dwCRC:08X}")
    return ret


def remove_suffix(file: DFUFile) -> int:
    """remove suffix from DFU file"""
    ret: int

    ret = parse_dfu_suffix(file)
    if ret <= 0:
        return 0

    if hasattr(os, 'ftruncate'):
        try:
            with open(file.name, 'r+', encoding='utf-8') as f:
                f.truncate(file.size - file.suffix_len)
            _logger.info("DFU suffix removed")
        except OSError as e:
            raise GeneralError(f"Error truncating file: {e}")
    else:
        _logger.error("Suffix removal not implemented on this platform")
    return 1


def add_suffix(file: DFUFile, pid: int, vid: int, did: int) -> None:
    """Add suffix to DFU file"""
    ret: int

    file.idProduct = pid
    file.idVendor = vid
    file.bcdDevice = did

    ret = lmdfu.generate_dfu_suffix(file)
    if ret < 0:
        try:
            raise OSError("generate")
        except OSError as e:
            raise GeneralError(e)
    _logger.info("New DFU suffix added.")


def hex2int(string: str) -> float:
    return int(string, 16)


def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add cli options"""
    parser.add_argument('-V', '--version', action='version',
                        version=VERSION,
                        help='Print the version number')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-c', '--check',
                       const=Mode.CHECK, dest='mode', action='store_const',
                       help='Check DFU suffix of <file>')
    group.add_argument('-a', '--add',
                       const=Mode.ADD, dest='mode', action='store_const',
                       help='Add DFU suffix to <file>')
    group.add_argument('-D', '--delete',
                       const=Mode.DEL, dest='mode', action='store_const',
                       help='Delete DFU suffix from <file>')

    parser.add_argument('file', action='store', metavar='<file>',
                        type=argparse.FileType('r+b'), default=None,
                        help="Target filename")

    parser.add_argument('-p', '--pid', action='store', metavar="<productID>",
                        required=False,
                        type=hex2int, help='Add product ID into DFU suffix in <file>')
    parser.add_argument('-v', '--vid', action='store', metavar="<vendorID>",
                        required=False,
                        type=hex2int, help='Add vendor ID into DFU suffix in <file>')
    parser.add_argument('-d', '--did', action='store', metavar="<deviceID>",
                        required=False,
                        type=hex2int, help='Add device ID into DFU suffix in <file>')
    parser.add_argument('-S', '--spec', dest='spec', action='store',
                        metavar="<specID>", choices=("0x0100", "0x011a"), default="0x0100",
                        help='Add DFU specification ID into DFU suffix in <file>')


@handle_exceptions(_logger)
def main() -> None:
    """cli entry point for suffix"""
    parser = argparse.ArgumentParser(
        prog='pydfuutil-suffix',
        exit_on_error=False,
    )
    add_cli_options(parser)
    print(f"v{__version__}")
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as err:
        parser.print_help()
        raise GeneralError(err)


    file = DFUFile(name=args.file.name, file_p=args.file)
    mode = args.mode

    try:
        pid = int(args.pid, 16) if args.pid else 0xffff
        vid = int(args.vid, 16) if args.vid else 0xffff
        did = int(args.did, 16) if args.did else 0xffff
    except:
        raise MissuseError("--vid, --pid, --did must be an 2-byte hex "
                           "in 0xFFFF format")

    spec = int(args.spec, 16)

    if mode == Mode.ADD:
        file.load(SuffixReq.NO_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.idVendor = vid
        file.idVendor = pid
        file.bcdDevice = did
        file.bcdDFU = spec
        # always write suffix, rewrite prefix if there was one
        file.dump(True, file.size.prefix != 0)
        _logger.info("Suffix successfully added to file")

    elif mode == Mode.CHECK:
        file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.show_suffix_and_prefix()

    elif mode == Mode.DEL:
        file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.dump(False, file.size.prefix != 0)
        if file.size.suffix:
            _logger.info("Suffix successfully removed from file")

    else:
        parser.print_help()
        raise MissuseError

    sys.exit(0)


if __name__ == '__main__':
    main()

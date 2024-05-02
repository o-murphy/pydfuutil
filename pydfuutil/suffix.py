"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import argparse
import os
import sys
from enum import IntEnum
import importlib.metadata

from pydfuutil import __copyright__
from pydfuutil import lmdfu
from pydfuutil.dfu_file import DFUFile, parse_dfu_suffix
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


class LmdfuMode(IntEnum):
    """LMDFU suffix operate mode"""
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


def print_version() -> None:
    """
    Prints dfu-suffix version to console
    """
    print(f'pydfuutil-suffix " {__version__} "\n')
    print(f'{__copyright__[0]}\n'
          'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


OPTS = (
    ("help", 0, 0, 'h'),
    ("version", 0, 0, 'V'),
    ("delete", 1, 0, 'D'),
    ("pid", 1, 0, 'p'),
    ("vid", 1, 0, 'v'),
    ("did", 1, 0, 'd'),
    ("check", 1, 0, 'c'),
    ("add", 1, 0, 'a'),
    ("stellaris-address", 1, 0, 's'),
    ("stellaris", 0, 0, 'T'),
)


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
            _logger.error(f"Error truncating file: {e}")
            sys.exit(1)
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
            _logger.error(e)
            sys.exit(1)
    _logger.info("New DFU suffix added.")


def _get_arg_parser():
    """Get custom argument parser"""

    class CustomHelpFormatter(argparse.HelpFormatter):
        """Custom argument parser formatter"""

        def add_argument(self, action):
            if action.dest == 'help':
                action.help = 'Print this help message'
            super().add_argument(action)

    parser = argparse.ArgumentParser(
        prog='dfu-suffix',
        # description="",
        # epilog='Text at the bottom of help',
        # conflict_handler='resolve',
        exit_on_error=False,
        # add_help=True,
        formatter_class=CustomHelpFormatter
    )

    parser.add_argument('-V', '--version', action='version',
                        version=f'{parser.prog} " v{__version__} "',
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
                        type=lambda x: int(x, 16), help='Add product ID into DFU suffix in <file>')
    parser.add_argument('-v', '--vid', action='store', metavar="<vendorID>",
                        required=False,
                        type=lambda x: int(x, 16), help='Add vendor ID into DFU suffix in <file>')
    parser.add_argument('-d', '--did', action='store', metavar="<deviceID>",
                        required=False,
                        type=lambda x: int(x, 16), help='Add device ID into DFU suffix in <file>')
    parser.add_argument('-s', '--stellaris-address', dest='lmdfu_flash_address',
                        metavar="<address>", type=int, help='Specify lmdfu address for LMDFU_ADD')
    parser.add_argument('-T', '--stellaris', dest='lmdfu_mode', action='store_const',
                        const=LmdfuMode.CHECK, help='Set lmdfu mode to LMDFU_CHECK')

    return parser


def get_args(parser, argv):
    """parse command line arguments"""
    print_version()
    try:
        args = parser.parse_args(argv)
    except argparse.ArgumentError as err:
        parser.print_help()
        _logger.error(err)
        sys.exit(1)
    return args


def main(argv) -> None:
    """main executable"""
    if argv[0] == __file__:
        argv.pop(0)

    parser = _get_arg_parser()
    args = get_args(parser, argv)

    lmdfu_mode = LmdfuMode.NONE
    lmdfu_flash_address: int = 0
    lmdfu_prefix: int = 0

    empty = 0xffff

    file = DFUFile(args.file.name)
    file.file_p, mode = args.file, args.mode

    pid = args.pid if args.pid else empty
    vid = args.vid if args.vid else empty
    did = args.did if args.did else empty

    if args.lmdfu_flash_address:
        lmdfu_mode, lmdfu_flash_address = LmdfuMode.ADD, args.lmdfu_flash_address

    if args.lmdfu_mode:
        lmdfu_mode = LmdfuMode.CHECK

    if mode == Mode.DEL and lmdfu_mode == LmdfuMode.CHECK:
        lmdfu_mode = LmdfuMode.DEL

    if mode != Mode.NONE:
        try:
            if mode == Mode.ADD:

                if check_suffix(file):
                    if lmdfu_prefix:
                        lmdfu.check_prefix(file)
                    _logger.warning("Please remove existing DFU suffix before adding a new one.")
                    sys.exit(1)

                if lmdfu_mode == LmdfuMode.ADD:
                    if lmdfu.check_prefix(file):
                        _logger.info("Adding new anyway")
                    lmdfu.add_prefix(file, lmdfu_flash_address)

                add_suffix(file, pid, vid, did)

            elif mode == Mode.CHECK:
                # Note: could open read-only here
                check_suffix(file)
                if lmdfu_mode == LmdfuMode.CHECK:
                    lmdfu.check_prefix(file)

            elif mode == Mode.DEL:
                if (not remove_suffix(file)
                        and lmdfu_mode == LmdfuMode.DEL
                        and lmdfu.check_prefix(file)):
                    lmdfu.remove_prefix(file)
                    sys.exit(1)

            else:
                parser.print_help()
                sys.exit(2)

            if lmdfu_mode == LmdfuMode.DEL and check_suffix(file):
                _logger.warning(
                    "DFU suffix exist. "
                    "Remove suffix before using -T or use it with -D to delete suffix")
                sys.exit(1)

            if lmdfu_mode == LmdfuMode.DEL and lmdfu.check_prefix(file):
                lmdfu.remove_prefix(file)

        except Exception as error:
            _logger.error(error)
            sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv)

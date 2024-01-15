"""
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import argparse
import os
import sys
from enum import IntEnum

from pydfuutil import __version__, __copyright__
from pydfuutil.dfu_file import *
from pydfuutil.lmdfu import *
from pydfuutil.logger import get_logger

logger = get_logger("dfu-suffix")


class Mode(IntEnum):
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


class LmdfuMode(IntEnum):
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


# def help_() -> None:
#     print("Usage: dfu-suffix [options] <file>"
#           "  -h --help\tPrint this help message"
#           "  -V --version\tPrint the version number"
#           "  -D --delete\tDelete DFU suffix from <file>"
#           "  -p --pid\tAdd product ID into DFU suffix in <file>"
#           "  -v --vid\tAdd vendor ID into DFU suffix in <file>"
#           "  -d --did\tAdd device ID into DFU suffix in <file>"
#           "  -c --check\tCheck DFU suffix of <file>"
#           "  -a --add\tAdd DFU suffix to <file>"
#           )
# TODO: implement
#     print("  -s --stellaris-address <address>  Add TI Stellaris address "
#           "prefix to <file>,\n\t\tto be used together with -a"
#           "  -T --stellaris  Act on TI Stellaris extension prefix of "
#           "<file>, to be used\n\t\tin combination with -D or -c"
#           )


def print_version() -> None:
    """
    Prints dfu-suffix version to console
    """
    print(f'dfu-suffix " {__version__} "\n')
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
    ret: int

    ret = parse_dfu_suffix(file)
    if ret > 0:
        print(f"The file {file.name} contains a DFU suffix with the following properties:")
        print(f"BCD device:\t0x{file.bcdDevice:04X}")
        print(f"Product ID:\t0x{file.idProduct:04X}")
        print(f"Vendor ID:\t0x{file.idVendor:04X}")
        print(f"BCD DFU:\t0x{file.bcdDFU:04X}")
        print(f"Length:\t\t{file.suffixlen}")
        print(f"CRC:\t\t0x{file.dwCRC:08X}")
    return ret


def remove_suffix(file: DFUFile) -> int:
    ret: int

    ret = parse_dfu_suffix(file)
    if ret <= 0:
        return 0

    if hasattr(os, 'ftruncate'):
        try:
            with open(file.name, 'r+') as f:
                f.truncate(file.size - file.suffixlen)
            logger.info("DFU suffix removed")
        except OSError as e:
            logger.error(f"Error truncating file: {e}")
            exit(1)
    else:
        logger.error("Suffix removal not implemented on this platform")
    return 1


def add_suffix(file: DFUFile, pid: int, vid: int, did: int) -> None:
    ret: int

    file.idProduct = pid
    file.idVendor = vid
    file.bcdDevice = did

    ret = generate_dfu_suffix(file)
    if ret < 0:
        try:
            raise OSError("generate")
        except OSError as e:
            logger.error(e)
            exit(1)
    logger.info("New DFU suffix added.")


def _get_argparser():
    class CustomHelpFormatter(argparse.HelpFormatter):
        def add_argument(self, action):
            if action.dest == 'help':
                action.help = 'Print this help message'
            super(CustomHelpFormatter, self).add_argument(action)

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

    group.add_argument('-c', '--check', metavar="<file>", const=Mode.CHECK, dest='mode', action='store_const',
                       help='Check DFU suffix of <file>')
    group.add_argument('-a', '--add', metavar="<file>", const=Mode.ADD, dest='mode', action='store_const',
                       help='Add DFU suffix to <file>')
    group.add_argument('-D', '--delete', metavar="<file>", const=Mode.DEL, dest='mode', action='store_const',
                       help='Delete DFU suffix from <file>')

    parser.add_argument('file', action='store', type=argparse.FileType('r+b'), metavar='<file>',
                        help="Target filename")

    parser.add_argument('-p', '--pid', action='store', metavar="<productID>", required=False,
                        type=lambda x: int(x, 16), help='Add product ID into DFU suffix in <file>')
    parser.add_argument('-v', '--vid', action='store', metavar="<vendorID>", required=False,
                        type=lambda x: int(x, 16), help='Add vendor ID into DFU suffix in <file>')
    parser.add_argument('-d', '--did', action='store', metavar="<deviceID>", required=False,
                        type=lambda x: int(x, 16), help='Add device ID into DFU suffix in <file>')
    # parser.add_argument('-S', '--spec', action='store', metavar="<specID>", required=False,
    #                     help='Add DFU specification ID into DFU suffix in <file>')
    parser.add_argument('-s', '--stellaris-address', dest='lmdfu_flash_address',
                        metavar="<address>", type=int, help='Specify lmdfu address for LMDFU_ADD')
    parser.add_argument('-T', '--stellaris', dest='lmdfu_mode', action='store_const',
                        const=LmdfuMode.CHECK, help='Set lmdfu mode to LMDFU_CHECK')

    return parser


def get_args(parser):
    parser = _get_argparser()
    print_version()
    try:
        args = parser.parse_args()
    except Exception as err:
        parser.print_help()
        logger.error(err)
        sys.exit(1)
    return args


def main() -> None:
    parser = _get_argparser()
    args = get_args(parser)

    # file = args.check or args.add or args.delete
    # file_name = file.name

    lmdfu_mode = LmdfuMode.NONE
    lmdfu_flash_address: int = 0
    lmdfu_prefix: int = 0
    end: str

    pid: int = 0xffff
    vid: int = 0xffff
    did: int = 0xffff

    file = DFUFile(args.file.name)
    file.filep = args.file
    mode = args.mode

    if args.pid:
        pid = args.pid
    if args.vid:
        vid = args.vid
    if args.did:
        did = args.did
    if args.lmdfu_flash_address:
        lmdfu_mode = LmdfuMode.ADD
        lmdfu_flash_address = args.lmdfu_flash_address
    if args.lmdfu_mode:
        lmdfu_mode = LmdfuMode.CHECK

    if mode == Mode.DEL and lmdfu_mode == LmdfuMode.CHECK:
        lmdfu_mode = LmdfuMode.DEL

    if mode != Mode.NONE:
        try:
            # with open(file.name, "r+b") as file.filep:

            if mode == Mode.ADD:

                if check_suffix(file):
                    if lmdfu_prefix:
                        lmdfu_check_prefix(file)
                    logger.warning("Please remove existing DFU suffix before adding a new one.")
                    sys.exit(1)

                if lmdfu_mode == LmdfuMode.ADD:
                    if lmdfu_check_prefix(file):
                        logger.info("Adding new anyway")
                    lmdfu_add_prefix(file, lmdfu_flash_address)

                add_suffix(file, pid, vid, did)

            elif mode == Mode.CHECK:
                # FIXME: could open read-only here
                check_suffix(file)
                if lmdfu_mode == LmdfuMode.CHECK:
                    lmdfu_check_prefix(file)

            elif mode == Mode.DEL:
                if not remove_suffix(file):
                    if lmdfu_mode == LmdfuMode.DEL:
                        if lmdfu_check_prefix(file):
                            lmdfu_remove_prefix(file)
                            sys.exit(1)

            else:
                parser.print_help()
                sys.exit(2)

            if lmdfu_mode == LmdfuMode.DEL:
                if check_suffix(file):
                    logger.warning("DFU suffix exist. Remove suffix before using -T or use it with -D to delete suffix")
                    sys.exit(1)
                else:
                    if lmdfu_check_prefix(file):
                        lmdfu_remove_prefix(file)

        except Exception as error:
            logger.error(error)
            sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

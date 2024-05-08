"""
dfu-prefix
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
import argparse
import importlib.metadata
import sys
from enum import IntEnum

from pydfuutil import __copyright__
from pydfuutil.dfu_file import DFUFile, PrefixType, SuffixReq, PrefixReq
from pydfuutil.exceptions import handle_exceptions, GeneralError, MissUseError, DataError
from pydfuutil.logger import logger

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

_logger = logger.getChild('prefix')

VERSION = (f'pydfuutil-prefix " v{__version__} "\n {__copyright__[0]}\n'
           f'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


def hex2int(string: str) -> float:
    return int(string, 16)


def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add cli options"""
    parser.add_argument('-V', '--version', action='version',
                        version=VERSION,
                        help='Print the version number')

    parser.add_argument('file', action='store', metavar='<file>',
                        type=argparse.FileType('r+b'), default=None,
                        help="Target filename")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-c', '--check',
                       const=Mode.CHECK, dest='mode', action='store_const',
                       help='Check DFU suffix of <file>')
    group.add_argument('-D', '--delete',
                       const=Mode.DEL, dest='mode', action='store_const',
                       help='Delete DFU suffix from <file>')
    group.add_argument('-a', '--add',
                       const=Mode.ADD, dest='mode', action='store_const',
                       help='Add DFU suffix to <file>')

    add_group = parser.add_argument_group("In combination with -a")

    add_group.add_argument('-s', '--stellaris-address',
                           action='store', metavar="<address>", dest='s',
                           help='Add TI Stellaris address prefix to <file>')

    del_check_group = parser.add_argument_group("In combination with -a or -D or -c")
    del_check_group.add_argument('-T', '--stellaris',
                                 action='store_const', dest='type',
                                 const=PrefixType.LMDFU_PREFIX,
                                 help='Act on TI Stellaris address prefix of <file>')

    all_group = parser.add_argument_group("In combination with -a or -D or -c")
    all_group.add_argument('-L', '--lpc-prefix',
                           action='store_const', dest='type',
                           const=PrefixType.LPCDFU_UNENCRYPTED_PREFIX,
                           help='Use NXP LPC DFU prefix format')


class Mode(IntEnum):
    """DFU prefix operate mode"""
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


@handle_exceptions(_logger)
def main():
    """cli entry point for prefix"""
    parser = argparse.ArgumentParser(
        prog='pydfuutil-prefix',
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
    prefix_type = args.type if args.type else PrefixType.ZERO_PREFIX

    try:
        lmdfu_flash_address = hex2int(args.s) if args.s else 0
    except ValueError:
        raise MissUseError("--stellaris-address must be a 2-byte hex "
                           "in 0xFFFF format")

    if not file.name:
        _logger.error("You need to specify a filename")
        parser.print_help()
        raise MissUseError

    if mode is Mode.ADD:
        if prefix_type is PrefixType.ZERO_PREFIX:
            raise MissUseError("Prefix type must be specified")
        file.load(SuffixReq.MAYBE_SUFFIX, PrefixReq.NO_PREFIX)
        file.lmdfu_address = lmdfu_flash_address
        file.prefix_type = prefix_type
        _logger.info("Adding prefix to file")
        file.dump(file.size.suffix != 0, True)

    elif mode is Mode.CHECK:
        file.load(SuffixReq.MAYBE_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.show_suffix_and_prefix()
        if (prefix_type > PrefixType.ZERO_PREFIX
                and not file.prefix_type is prefix_type):
            raise DataError("No prefix of requested type")

    elif mode is Mode.DEL:
        file.load(SuffixReq.MAYBE_SUFFIX, PrefixReq.NEEDS_PREFIX)
        if (prefix_type > PrefixType.ZERO_PREFIX
                and not file.prefix_type is prefix_type):
            raise DataError("No prefix of requested type")
        _logger.info("Removing prefix from file")
        # if there was a suffix, rewrite it
        file.dump(file.size.suffix != 0, False)

    else:
        parser.print_help()
        raise MissUseError

    sys.exit(0)


if __name__ == "__main__":
    main()

"""
dfu-suffix
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
from pydfuutil.dfu_file import DfuFile, SuffixReq, PrefixReq
from pydfuutil.exceptions import Errx, UsageError, except_and_safe_exit
from pydfuutil.logger import logger

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

_logger = logger.getChild('suffix')


class Mode(IntEnum):
    """DFU suffix operate mode"""
    NONE = 0x1
    ADD = 0x2
    DEL = 0x3
    CHECK = 0x4


VERSION = (f'pydfuutil-suffix " v{__version__} "\n {__copyright__[0]}\n'
           f'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


def hex2int(string: str) -> int:
    """Convert a hexadecimal string to an int"""
    try:
        return int(string, 16)
    except ValueError as e:
        raise UsageError("--vid, --pid, --did must be a 2-byte hex "
                           "in 0xFFFF format") from e


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


@except_and_safe_exit(_logger)
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
    except argparse.ArgumentError as e:
        parser.print_help()
        raise Errx(e) from e

    file = DfuFile(name=args.file.name, file_p=args.file)
    mode = args.mode

    pid = args.pid if args.pid else 0xffff
    vid = args.vid if args.vid else 0xffff
    did = args.did if args.did else 0xffff

    spec = int(args.spec, 16)

    if mode is Mode.ADD:
        file.load(SuffixReq.NO_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.idVendor = vid
        file.idProduct = pid
        file.bcdDevice = did
        file.bcdDFU = spec
        # always write suffix, rewrite prefix if there was one
        file.dump(True, file.size.prefix != 0)
        _logger.info("Suffix successfully added to file")

    elif mode is Mode.CHECK:
        file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.show_suffix_and_prefix()

    elif mode is Mode.DEL:
        file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.MAYBE_PREFIX)
        file.dump(False, file.size.prefix != 0)
        if file.size.suffix:
            _logger.info("Suffix successfully removed from file")

    else:
        parser.print_help()
        raise UsageError

    sys.exit(0)


if __name__ == '__main__':
    main()

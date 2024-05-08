import argparse
import importlib.metadata
import sys

from pydfuutil import __copyright__
from pydfuutil.logger import logger
from pydfuutil.exceptions import handle_exceptions, GeneralError, MissuseError

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

_logger = logger.getChild('lsusb')

VERSION = (f'pydfuutil-lsusb " v{__version__} "\n {__copyright__[0]}\n'
           f'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


@handle_exceptions(_logger)
def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add cli options"""

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase verbosity (show descriptors)')
    parser.add_argument('-s', action='store',
                        metavar="[[bus]:][devnum]",
                        help='Show only devices with specified device '
                             'and/or bus numbers (in decimal)')
    parser.add_argument('-d', metavar='vendor:[product]', action='store',
                        help='Show only devices with the specified vendor '
                             'and product ID numbers (in hexadecimal)')
    parser.add_argument('-D', metavar='device', action='store',
                        help='Selects which device lsusb will examine')
    parser.add_argument('-t', '--tree', action='store_true',
                        help='Dump the physical USB device hierarchy as a tree')
    parser.add_argument('-V', '--version', action='version',
                        version=VERSION,
                        help='Print the version number')
    parser.add_argument('-h', '--help', action='store_true',
                        help='Show this help message and exit')


def parse_spec(string: str) -> ([int, None], [int, None]):
    try:
        bus, devnum = None, None
        if ":" == string:
            return bus, devnum
        elif ":" in string:
            _bus, _devnum, *_ = string.split(":")
            if _bus and _devnum:
                bus, devnum = int(_bus), int(_devnum)
            if not _devnum:
                bus, devnum = int(_bus), None
            if not _bus:
                bus = None
        else:
            bus, devnum = 1, int(string)
        return bus, devnum
    except ValueError:
        raise MissuseError(f"Wrong -s argument value '{string}'")


def parse_vid_pid(string: str) -> ([int, None], [int, None]):
    try:
        vid, pid = None, None
        if ":" == string:
            return vid, pid
        elif ":" in string:
            _vid, _pid, *_ = string.split(":")
            if _vid:
                vid = int(_vid, 16)
            if _pid:
                pid = int(_pid, 16)
        else:
            raise ValueError
        return vid, pid
    except ValueError:
        raise MissuseError(f"Wrong -s argument value '{string}'")


@handle_exceptions(_logger)
def main():
    """cli entry point for lsusb"""
    parser = argparse.ArgumentParser(
        prog='pydfuutil-prefix',
        exit_on_error=False,
        add_help=False
    )
    add_cli_options(parser)
    print(f"List USB devices\nv{__version__}")

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as err:
        parser.print_help()
        raise GeneralError(err)

    if args.help:
        parser.print_help()
        sys.exit(0)

    verbose = args.verbose
    bus, devnum = None, None
    vid, pid = None, None
    if args.s:
        bus, devnum = parse_spec(args.s)
    if args.d:
        vid, pid = parse_vid_pid(args.d)
    if args.D:
        parser.print_help()
        raise GeneralError("This version of lsusb does not support -D option")
    if args.tree:
        parser.print_help()
        raise GeneralError("This version of lsusb does not support --tree option")



if __name__ == '__main__':
    main()

import argparse
import importlib.metadata
import sys

from pydfuutil import __copyright__
from pydfuutil.logger import logger
from pydfuutil.exceptions import handle_exceptions, GeneralError, MissuseError
import usb.core
import usb._lookup as _lu

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

    class VidPidAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):

            def validate_int(val, base: int = 10):
                try:
                    return int(val, base) if val not in (None, '') else None
                except ValueError as err:
                    parser.print_help()
                    parser.error(f"-d format should be vendor:[product] "
                                 f"vendor and product ID numbers (in hexadecimal)")

            if values.count(":") > 1:
                validate_int(None)
            vid, pid = None, None
            if ":" in values:
                vid, pid = values.split(":")
            elif values.startswith(":"):
                pid = values[1:]
            elif values.endswith(":"):
                vid = values[:-1]
            else:
                vid = values
            setattr(namespace, "vid", validate_int(vid, 16))
            setattr(namespace, "pid", validate_int(pid, 16))

    class BusDevAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):

            def validate_int(val, base: int = 10):
                try:
                    return int(val, base) if val not in (None, '') else None
                except ValueError as err:
                    parser.print_help()
                    parser.error(f"-s format should be [[bus]:][devnum] "
                                 f"device and/or bus numbers (in decimal)")

            if values.count(":") > 1:
                validate_int(None)
            bus, devnum = None, None
            if ":" in values:
                bus, devnum = values.split(":")
            elif values.startswith(":"):
                devnum = values[1:]
            elif values.endswith(":"):
                bus = values[:-1]
            elif values == ":":
                pass
            else:
                devnum = values
            setattr(namespace, "bus", validate_int(bus))
            setattr(namespace, "address", validate_int(devnum))

    class SimulateUnixPath(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            def validate_int(val, base: int = 10):
                try:
                    return int(val, base) if val not in (None, '') else None
                except ValueError as err:
                    parser.print_help()
                    parser.error("-D option have to be in format '/dev/bus/usb/<bus>/<port>")

            setattr(namespace, "D", values)
            if not values.startswith('/dev/bus/usb/'):
                parser.error("-D option have to be in format '/dev/bus/usb/<bus>/<port>")
            bus_devnum = values.split('/')[4:]
            if 1 > len(bus_devnum) > 2:
                parser.error("-D option have to be in format '/dev/bus/usb/<bus>/<port>")
            bus, devnum = bus_devnum
            setattr(namespace, "bus", validate_int(bus))
            setattr(namespace, "address", validate_int(devnum))

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase verbosity (show descriptors)')
    parser.add_argument('-s', action=BusDevAction,
                        metavar="[[bus]:][devnum]",
                        help='Show only devices with specified device '
                             'and/or bus numbers (in decimal)')
    parser.add_argument('-d', action=VidPidAction,
                        metavar='vendor:[product]',
                        help='Show only devices with the specified vendor '
                             'and product ID numbers (in hexadecimal)')

    if not sys.platform.startswith('win'):
        parser.add_argument('-D', metavar='device',
                            action='store',
                            help='Selects which device lsusb will examine')
        parser.add_argument('-t', '--tree', action='store_true',
                            help='Dump the physical USB device hierarchy as a tree')
    else:
        parser.add_argument('-D', metavar='device',
                            action=SimulateUnixPath,
                            help='Selects which device lsusb will examine '
                                 'by UNIX-like path simulate')
        parser.add_argument('-t', '--tree', action='store_true',
                            help='Simulate UNIX-like physical USB device hierarchy')

    parser.add_argument('-V', '--version', action='version',
                        version=VERSION,
                        help='Print the version number')
    parser.add_argument('-h', '--help', action='store_true',
                        help='Show this help message and exit')


def device_find_filter(dev: usb.core.Device,
                       vid: int = None,
                       pid: int = None,
                       bus: int = None,
                       address: int = None):
    # if path is not None and dev.device_address != path:
    #     return False
    if bus is not None and dev.bus != bus:
        return False
    if address is not None and dev.address != address:
        return False
    if vid is not None and dev.idVendor != vid:
        return False
    if pid is not None and dev.idProduct != pid:
        return False
    return True


def list_devices(vid: int = None,
                 pid: int = None,
                 bus: int = None,
                 address: int = None,
                 verbose=False):
    def custom_match(dev):
        return device_find_filter(dev, vid, pid, bus, address)

    print(usb.core.show_devices(verbose, custom_match=custom_match))
    sys.exit(0)


def iter_devices(vid: int = None,
                 pid: int = None,
                 bus: int = None,
                 address: int = None):
    def custom_match(dev):
        return device_find_filter(dev, vid, pid, bus, address)

    return usb.core.find(find_all=True, custom_match=custom_match)


def sym_unix_dev_tree(vid: int = None,
                      pid: int = None,
                      bus: int = None,
                      address: int = None,
                      verbose: bool = False):
    ctx = iter_devices(vid, pid, bus, address)
    for dev in ctx:
        dev_class = usb.core._try_lookup(_lu.device_classes, dev.bDeviceClass)
        # dev_driver =
        manufacturer = usb.util.get_string(dev, dev.iManufacturer)
        product = usb.util.get_string(dev, dev.iProduct)
        print(f"/:\tBus {dev.bus:02}.Port {dev.port_number:01}: "
              f"Dev {dev.address:01}, Class={dev_class}")
        if verbose:
            print(f"ID {dev.idVendor:04x}:{dev.idProduct:04x} "
                  f"{manufacturer}, {product}")


@handle_exceptions(_logger)
def main():
    """cli entry point for lsusb"""
    parser = argparse.ArgumentParser(
        prog='pydfuutil-prefix',
        exit_on_error=False,
        add_help=False
    )
    parser.set_defaults(bus=None, address=None,
                        vid=None, pid=None, path=None, tree=False)
    add_cli_options(parser)
    print(f"List USB devices\nv{__version__}")

    try:
        args = parser.parse_args()
    except (argparse.ArgumentError, argparse.ArgumentTypeError) as err:
        raise GeneralError(err)

    if args.help:
        parser.print_help()
        sys.exit(0)

    verbose = args.verbose
    vid, pid, bus, address = args.vid, args.pid, args.bus, args.address
    if not sys.platform.startswith('win'):

        if args.D:
            parser.print_help()
            raise parser.error("This version of lsusb does not support -D option")
        if args.tree:
            parser.print_help()
            raise parser.error("This version of lsusb does not support --tree option")
    else:
        if args.D:
            list_devices(vid, pid, bus, address, verbose)
        if args.tree:
            sym_unix_dev_tree(vid, pid, bus, address, verbose)

    if not args.D and not args.tree:
        list_devices(vid, pid, bus, address, verbose)


if __name__ == '__main__':
    main()

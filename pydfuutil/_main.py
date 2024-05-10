"""
pydfuutil
dfu-util
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

Based on existing code of dfu-programmer-0.4

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
from enum import Enum

from pydfuutil.logger import logger
from pydfuutil.dfu_util import DfuUtil

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

VERSION = (f"pydfuutil v{__version__}\n\n"
           f"2023 Yaroshenko Dmytro (https://github.com/o-murphy)\n")

DfuUtil.dfu_if = None
DfuUtil.match_path = None
DfuUtil.match_vendor = -1
DfuUtil.match_product = -1
DfuUtil.match_vendor_dfu = -1
DfuUtil.match_product_dfu = -1
DfuUtil.match_config_index = -1
DfuUtil.match_iface_index = -1
DfuUtil.match_iface_alt_index = -1
DfuUtil.match_devnum = -1
DfuUtil.match_iface_alt_name = None
DfuUtil.match_serial = None
DfuUtil.match_serial_dfu = None

DfuUtil.dfu_root = None

DfuUtil.path_buf = None


class Mode(Enum):
    """dfu-util cli mode"""
    NONE = 0
    # VERSION = 1
    LIST = 2
    DETACH = 3
    UPLOAD = 4
    DOWNLOAD = 5


def parse_match_value(string: str, default_value: int) -> int:
    ...


def parse_vendprod(string: str) -> int:
    ...
    # Default to match any DFU device in runtime or DFU mode


def parse_serial(string: str) -> None:
    ...


def parse_number(string: str, nmb: chr) -> int:
    ...


class ActionFileMode(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(option_string, values)
        if option_string == '-U':
            setattr(namespace, 'mode', Mode.UPLOAD)
        elif option_string == '-D':
            setattr(namespace, 'mode', Mode.DOWNLOAD)
        setattr(namespace, 'file', values)


options = (
    {
        'args': ('-V', '--version'),
        'action': 'version', 'version': VERSION,
        'help': "Print the version number"
    },
    {
        'args': ('-v', '--verbose'),
        'action': 'store_true',
        'help': "Print verbose debug statements"
    },
    {
        'args': ('-l', '--list'),
        'action': 'store_true',
        'help': "List the currently attached DFU capable USB devices"
    },
    {
        'args': ('-e', '--detach'),
        'action': 'store_true',
        'help': "Detach the currently attached DFU capable USB devices"
    },
    {
        'args': ('-E', '--detach-delay'),
        'help': "Time to wait before reopening a device after detach",
        'metavar': '<seconds>',
        'type': int,
        'default': 1
    },
    {
        'args': ('-d', '--device'),
        'help': "Specify Vendor/Product ID(s) of DFU device",
        'metavar': '<vid>:<pid>[,<vid_dfu>:<pid_dfu>]',
    },
    {
        'args': ('-n', '--devnum'),
        'help': "Match given device number (devnum from --list)",
        'metavar': '<dnum>',
        'type': int
    },
    {
        'args': ('-p', '--path'),
        'help': "Specify path to DFU device",
        'metavar': '<bus-port. ... .port>',
    },
    {
        'args': ('-c', '--cfg'),
        'help': "Specify the Configuration of DFU device",
        'metavar': '<config_nr>',
        'type': int
    },
    {
        'args': ('-i', '--intf'),
        'help': "Specify the DFU Interface number",
        'metavar': '<intf_nr>',
        'type': int
    },
    {
        'args': ('-S', '--serial'),
        'help': "Specify Serial String of DFU device",
        'metavar': '<serial_str>[,<serial_str_dfu>]',
    },
    {
        'args': ('-a', '--alt'),
        'help': "Specify the Altsetting of the DFU Interface",
        'metavar': '<alt>',
        'type': int
    },
    {
        'args': ('-t', '--transfer-size'),
        'help': "Specify the number of bytes per USB Transfer",
        'metavar': '<size>',
        'type': int
    },
    {
        'args': ('-U', '--upload'),
        'action': ActionFileMode,
        'help': "Read firmware from device into <file>",
        'metavar': '<file>',
    },
    {
        'args': ('-Z', '--upload-size'),
        'help': "Read firmware from device into <file>",
        'metavar': '<bytes>',
        'type': int
    },
    {
        'args': ('-D', '--download'),
        'action': ActionFileMode,
        'help': "Read firmware from device into <file>",
        'metavar': '<file>',
    },
    {
        'args': ('-R', '--reset'),
        'action': 'store_true',
        'help': "Issue USB Reset signalling once we're finished",
    },
    {
        'args': ('-w', '--wait'),
        'action': 'store_true',
        'help': "Wait for device to appear",
    },
    {
        'args': ('-s', '--dfuse-address'),
        'help': "ST DfuSe mode, "
                "specify target address for raw file download or upload. "
                "Not applicable for DfuSe file (.dfu) downloads",
        'metavar': '<address>'
    },
    {
        'args': ('-y', '--yes'),
        'action': 'store_true',
        'help': "Say yes to all prompts",
    },
)


def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add cli options"""
    for opt in options:
        args = opt.pop('args')
        parser.add_argument(*args, **opt)


def main():
    """Cli entry point"""

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog="pydfuutil",
        description="Python implementation of DFU-Util tools"
    )
    parser.set_defaults(file=None, mode=Mode.NONE)
    add_cli_options(parser)

    print(f"v{__version__}")
    # parse options
    args = parser.parse_args()

    expected_size: int = 0
    transfer_size: int = 0
    mode = Mode.NONE
    final_reset: bool = False
    wait_device: bool = False
    dfuse_device: bool = False
    dfuse_options = None
    detach_delay = 5

    if args.verbose:
        ...


if __name__ == '__main__':
    main()

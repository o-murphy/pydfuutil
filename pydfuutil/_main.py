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
import logging
import os
import sys
from enum import Enum

import usb.core
from usb.backend.libusb1 import LIBUSB_ERROR_PIPE

from pydfuutil import dfuse, dfu
from pydfuutil.dfu_file import DfuFile, SuffixReq, PrefixReq
from pydfuutil.dfu_util import DfuUtil, probe_devices, list_dfu_interfaces, disconnect_devices
from pydfuutil.exceptions import MissUseError, _IOError, except_and_safe_exit
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.usb_dfu import BmAttributes

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

VERSION = (f"pydfuutil v{__version__}\n\n"
           f"2023 Yaroshenko Dmytro (https://github.com/o-murphy)\n")

usb_logger = logging.getLogger('usb')

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


def parse_serial(string: [str, None]) -> None:
    if string in (None, ''):
        return

    DfuUtil.match_serial = string
    comma_index = string.find(',')

    if comma_index == -1:
        DfuUtil.match_serial_dfu = DfuUtil.match_serial
    else:
        DfuUtil.match_serial_dfu = string[comma_index + 1:]
        DfuUtil.match_serial = string[:comma_index]

    if not DfuUtil.match_serial:
        DfuUtil.match_serial = None
    if not DfuUtil.match_serial_dfu:
        DfuUtil.match_serial_dfu = None


class ActionFile(argparse.Action):
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
        'help': "Print verbose debug statements",
    },
    {
        'args': ('-l', '--list'),
        'action': 'store_const', 'const': Mode.LIST, 'dest': 'mode',
        'help': "List the currently attached DFU capable USB devices"
    },
    {
        'args': ('-e', '--detach'),
        'action': 'store_const', 'const': Mode.DETACH, 'dest': 'mode',
        'help': "Detach the currently attached DFU capable USB devices"
    },
    {
        'args': ('-E', '--detach-delay'),
        'help': "Time to wait before reopening a device after detach",
        'metavar': '<seconds>',
        'type': int,
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
    },
    {
        'args': ('-t', '--transfer-size'),
        'help': "Specify the number of bytes per USB Transfer",
        'metavar': '<size>',
        'type': int
    },
    {
        'args': ('-U', '--upload'),
        'action': ActionFile,
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
        'action': ActionFile,
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


@except_and_safe_exit(logger)
def main():
    """Cli entry point"""

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog="pydfuutil",
        description="Python implementation of DFU-Util tools"
    )
    parser.set_defaults(
        verbose=False,
        mode=Mode.NONE,
        detach_delay=5,
        device=None,
        devnum=-1,
        path=-1,
        cfg=-1,
        intf=-1,
        serial=None,
        alt=None,
        transfer_size=0,
        upload_size=0,
        file=None,
        reset=False,
        wait=False,
        dfuse_address=None,
        yes=False,
    )
    add_cli_options(parser)

    print(f"v{__version__}")
    # parse options
    optargs = parser.parse_args()

    mode = optargs.mode
    dfuse_device: bool = False
    dfuse_options = None

    file = DfuFile(name=optargs.file)

    if optargs.verbose:
        logger.setLevel(logging.DEBUG)
        usb_logger.setLevel(logging.DEBUG)
        try:
            from libusb_package import __version__ as LIBUSB_API_VERSION
            logger.debug(f"libusb version {LIBUSB_API_VERSION}")
        except ImportError:
            logger.warning("libusb version is ancient")

    DfuUtil.match_path = optargs.path

    # Configuration
    DfuUtil.match_config_index = optargs.cfg

    # Interface
    DfuUtil.match_iface_index = optargs.intf

    # Interface Alternate Setting
    if optargs.alt:
        try:
            DfuUtil.match_iface_alt_index = int(optargs.alt)
        except ValueError:
            DfuUtil.match_iface_alt_name = optargs.alt
            DfuUtil.match_iface_alt_index = -1

    DfuUtil.match_devnum = optargs.devnum

    parse_serial(optargs.serial)

    detach_delay = optargs.detach_delay
    transfer_size = optargs.transfer_size
    expected_size = optargs.upload_size
    final_reset = optargs.reset
    wait_device = optargs.wait

    # print(optargs.dfuse_address)  # FIXME: DFUSE options

    print(DfuUtil)
    print(optargs)

    if mode is Mode.NONE and not dfuse_options:
        logger.error("You need to specify one of -D or -U")
        parser.print_help()
        raise MissUseError

    if DfuUtil.match_config_index == 0:
        # Handle "-c 0" (unconfigured device) as don't care
        DfuUtil.match_config_index = -1

    if mode is Mode.DOWNLOAD:
        file.load(SuffixReq.MAYBE_SUFFIX, PrefixReq.MAYBE_PREFIX)
        # If the user didn't specify product and/or vendor IDs to match
        # use any IDs from the file suffix for device matching
        if DfuUtil.match_vendor < 0 and file.idProduct != 0xffff:
            DfuUtil.match_vendor = file.idVendor
            logger.info(f"Match vendor ID from file: {DfuUtil.match_vendor:04x}")
        if DfuUtil.match_product < 0 and file.idProduct != 0xffff:
            DfuUtil.match_product = file.idProduct
            logger.info(f"Match product ID from file: {DfuUtil.match_product:04x}")
    elif mode is Mode.NONE and dfuse_options:
        # for DfuSe special commands, match any device
        mode = Mode.DOWNLOAD
        file.idVendor = 0xffff
        file.idProduct = 0xffff

    if wait_device:
        logger.info("Waiting for device, exit with ctrl-C")

    try:
        ctx = usb.core.find(find_all=True)
    except usb.core.USBError as e:
        raise _IOError(f"unable to initialize libusb: {e}") from e

    # probe
    def probe():
        nonlocal ctx
        probe_devices(ctx)

        if mode is Mode.LIST:
            list_dfu_interfaces()
            disconnect_devices()
            sys.exit(0)

        if DfuUtil.dfu_root is None:
            if wait_device:
                milli_sleep(20)
            else:
                logger.warning("No DFU capable USB device available")
                ctx = None
                return os.EX_IOERR
        elif file.bcdDFU == 0x11a and dfuse.multiple_alt(DfuUtil.dfu_root):
            logger.info("Multiple alternate interfaces for DfuSe file")
        elif DfuUtil.dfu_root.next is not None:
            #  We cannot safely support more than one DFU capable device
            #  with same vendor/product ID, since during DFU we need to do
            #  a USB bus reset, after which the target device will get a
            #  new address */
            raise _IOError("More than one DFU capable USB device found! "
                           "Try `--list' and specify the serial number "
                           "or disconnect all but one device")

        # We have exactly one device.
        # Its libusb_device is now in DfuUtil.dfu_root.dev

        logger.info("Opening DFU capable USB device...")
        # if DfuUtil.dfu_root.dev is not None:

        ret = usb.core.find(custom_match=lambda d: d == DfuUtil.dfu_root.dev)
        if ret is None:
            raise _IOError("Cannot open device")

        logger.info(f"Device ID {DfuUtil.dfu_root.vendor:04x}:{DfuUtil.dfu_root.vendor:04x}")
        # If first interface is DFU it is likely not proper run-time
        _bcd_dfu_ver = DfuUtil.dfu_root.func_dfu.bcdDFUVersion
        if DfuUtil.dfu_root.interface > 0:
            logger.info(f"Run-Time device DFU version {_bcd_dfu_ver:04x}")
        else:
            logger.info(f"Device DFU version {_bcd_dfu_ver:04x}")

        if optargs.verbose:
            _bm_attrs = DfuUtil.dfu_root.func_dfu.bmAttributes
            _debug_msg = f"DFU attributes: (0x{_bm_attrs:02x})"
            _debug_msg += (" bitCanDnload"
                           if _bm_attrs & BmAttributes.USB_DFU_CAN_DOWNLOAD
                           else "")
            _debug_msg += (" bitCanUpload"
                           if _bm_attrs & BmAttributes.USB_DFU_CAN_UPLOAD
                           else "")
            _debug_msg += (" bitManifestationTolerant"
                           if _bm_attrs & BmAttributes.USB_DFU_MANIFEST_TOL
                           else "")
            _debug_msg += (" bitWillDetach"
                           if _bm_attrs & BmAttributes.USB_DFU_WILL_DETACH
                           else "")
            logger.debug(_debug_msg)
            logger.debug(f"Detach timeout "
                         f"{DfuUtil.dfu_root.func_dfu.wDetachTimeOut} ms")

        # Transition from run-Time mode to DFU mode
        if DfuUtil.dfu_root.flags & dfu.IFF.DFU:
            # In the 'first round' during runtime mode, there can only be one
            # DFU Interface descriptor according to the DFU Spec.

            # FIXME: check if the selected device really has only one

            runtime_vendor = DfuUtil.dfu_root.vendor
            runtime_product = DfuUtil.dfu_root.product

            logger.info("Claiming USB DFU (Run-Time) Interface...")
            try:
                usb.util.claim_interface(DfuUtil.dfu_root.dev,
                                         DfuUtil.dfu_root.interface)
            except usb.core.USBError as e:
                raise _IOError(
                    f"Cannot claim interface {DfuUtil.dfu_root.interface}: {e}") from e

            # Needed for some devices where the DFU interface is not the first,
            # and should also be safe if there are multiple alt settings.
            # Otherwise, skip the request since it might not be supported
            # by the device and the USB stack may or may not recover
            if DfuUtil.dfu_root.interface > 0 or DfuUtil.dfu_root.flags & dfu.IFF.DFU:
                logger.info("Setting Alternate Interface zero...")
                try:
                    DfuUtil.dfu_root.dev.set_interface_altsetting(
                        DfuUtil.dfu_root.interface, 0)
                except usb.core.USBError as e:
                    raise _IOError(f"Cannot set alternate interface zero: {e}") from e

            logger.info("Determining device status...")

            try:
                _err = int(status := DfuUtil.dfu_root.get_status())
                if _err != LIBUSB_ERROR_PIPE:
                    logger.warning("Device does not implement get_status, assuming appIDLE")
                    status.bStatus = dfu.Status.OK
                    status.bwPollTimeout  = 0
                    status.bState  = dfu.State.APP_IDLE
                    status.iString = 0
                elif _err < 0:
                    raise _IOError(f"error get_status {_err}")
                else:
                    logger.info(f"DFU "
                                f"state({status.bState}) = {status.bState.to_string()}, "
                                f"status({status.bStatus}) = {status.bStatus.to_string()})")
            except usb.core.USBError as e:
                raise _IOError(f"error get_status: {e}")

            milli_sleep(status.bwPollTimeout)
            # line of main.c #527






    probe()


if __name__ == '__main__':
    main()

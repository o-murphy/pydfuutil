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
from typing import Optional, Literal

import usb.core
from usb.backend.libusb1 import LIBUSB_ERROR_PIPE, LIBUSB_ERROR_NOT_FOUND

from pydfuutil import dfuse, dfu, dfu_load
from pydfuutil.dfu_file import DfuFile, SuffixReq, PrefixReq
from pydfuutil.dfu_util import DfuUtil, probe_devices, list_dfu_interfaces, disconnect_devices
from pydfuutil.exceptions import UsageError, _IOError, except_and_safe_exit, SysExit, ProtocolError, Errx
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.quirks import QUIRK
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


def int_(value: [int, bytes, bytearray],
         order: Optional[Literal["little", "big"]] = 'little') -> int:
    """coerce value to int"""
    if isinstance(value, int):
        return value
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(value, order)
    raise TypeError("Unsupported type")


class ActionFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
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

    runtime_vendor, runtime_product = 0xffff, 0xffff

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

    if mode is Mode.NONE and not dfuse_options:
        logger.error("You need to specify one of -D or -U")
        parser.print_help()
        raise UsageError

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

    def check_status():
        # status_again
        logger.debug('Status again')
        logger.info("Determining device status...")
        if int(status := DfuUtil.dfu_root.get_status()) < 0:
            raise _IOError(f"error get_status")
        logger.info(f"state = {status.bState.to_string()}, "
                    f"status = {status.bStatus}")
        # if not DfuUtil.dfu_root.quirks & QUIRK.POLLTIMEOUT:
        milli_sleep(status.bwPollTimeout)

        if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
            raise ProtocolError("Device still in Run-Time Mode!")
        if status.bState == dfu.State.DFU_ERROR:
            logger.info("Clearing status")
            try:
                DfuUtil.dfu_root.clear_status()
            except usb.core.USBError as e:
                raise _IOError("error clear_status") from e
            check_status()
            return status
        if status.bState in (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_UPLOAD_IDLE):
            logger.info("Aborting previous incomplete transfer")
            try:
                DfuUtil.dfu_root.abort()
            except usb.core.USBError as e:
                raise _IOError("can't send DFU_ABORT") from e
            check_status()
            return status
        if status.bState == dfu.State.DFU_IDLE:
            return status
        else:
            return status

    def dfu_state():
        nonlocal transfer_size, file, dfuse_device, dfuse_options
        nonlocal runtime_vendor, runtime_product

        # # Note: uncomment on need
        # logger.info(f"Setting Configuration {dif.configuration}...")
        # try:
        #     dif.dev.set_configuration(dif.configuration)
        # except usb.core.USBError as e:
        #     raise Errx("Cannot set configuration")

        logger.info("Claiming USB DFU Interface")
        try:
            usb.util.claim_interface(DfuUtil.dfu_root.dev, DfuUtil.dfu_root.interface)
        except usb.core.USBError as e:
            raise _IOError(f"Cannot claim interface - {e}") from e

        if DfuUtil.dfu_root.flags & dfu.IFF.ALT:
            try:
                DfuUtil.dfu_root.dev.set_interface_altsetting(
                    DfuUtil.dfu_root.interface,
                    DfuUtil.dfu_root.altsetting
                )
            except usb.core.USBError as e:
                raise _IOError(f"Cannot set alternate interface: {e}") from e

        status = check_status()

        if dfu.Status.OK != status.bStatus:
            logger.warning(f"DFU Status: {status.bStatus.to_string()}")
            # Clear our status & try again.
            try:
                DfuUtil.dfu_root.clear_status()
            except usb.core.USBError as e:
                raise _IOError("USB communication error")
            if int(status := DfuUtil.dfu_root.get_status()) < 0:
                raise _IOError("USB communication error")
            if dfu.Status.OK != status.bStatus:
                raise ProtocolError(f"Status is not OK: {status.bStatus}")

            milli_sleep(status.bwPollTimeout)

        logger.info(f"DFU mode device DFU version "
                    f"{DfuUtil.dfu_root.func_dfu.bcdDFUVersion:04x}")

        if DfuUtil.dfu_root.func_dfu.bcdDFUVersion == 0x11a:
            dfuse_device = True
        elif dfuse_options:
            logger.warning("DfuSe option used on non-DfuSe device")

        # Get from device or user, warn if overridden
        func_dfu_transfer_size = DfuUtil.dfu_root.func_dfu.wTransferSize
        if func_dfu_transfer_size > 0:
            logger.error(f"Device returned transfer size {func_dfu_transfer_size}")
            if not transfer_size:
                transfer_size = func_dfu_transfer_size
            else:
                logger.warning("Overriding device-reported transfer size")
        else:
            if transfer_size <= 0:
                raise UsageError("Transfer size must be specified")

        # limited to 4k in libusb Linux backend
        if sys.platform.startswith("linux"):
            if transfer_size > 4096:
                transfer_size = 4096
                logger.info(f"Limited transfer size to {transfer_size}")

        if transfer_size < DfuUtil.dfu_root.bMaxPacketSize0:
            transfer_size = DfuUtil.dfu_root.bMaxPacketSize0
            logger.info(f"Adjusted transfer size to {transfer_size}")

        if mode is Mode.UPLOAD:
            # open for "exclusive" writing
            try:
                with open(file.name, 'wb') as file.file_p:
                    if dfuse_device or dfuse_options:
                        ret = dfuse.do_upload(DfuUtil.dfu_root, transfer_size,
                                              file, dfuse_options)
                    else:
                        ret = dfu_load.do_upload(DfuUtil.dfu_root, transfer_size, file)
                ret = SysExit.EX_IOERR if ret < 0 else SysExit.EX_OK
            except IOError:
                logger.warning(f"Cannot open file {file.name} for writing")
                ret = SysExit.EX_CANTCREAT

        elif mode is Mode.UPLOAD:
            # line 739
            if ((file.idVendor not in (0xffff, runtime_vendor)
                 or file.idProduct not in (0xffff, runtime_product))
                    and (file.idVendor not in (0xffff, DfuUtil.dfu_root.vendor)
                         or file.idProduct not in (0xffff, DfuUtil.dfu_root.product))):
                raise UsageError(f"Error: File ID {file.idVendor:04x}:{file.idProduct:04x} "
                                 f"does not match device "
                                 f"({runtime_vendor:04x}:{runtime_product:04x} "
                                 f"or {DfuUtil.dfu_root.vendor:04x}:{DfuUtil.dfu_root.product:04x})")

            if dfuse_device and dfuse_options and file.bcdDFU == 0x11a:
                ret = dfuse.do_download(DfuUtil.dfu_root, transfer_size,
                                      file, dfuse_options)
            else:
                ret = dfu_load.do_download(DfuUtil.dfu_root, transfer_size, file)

            ret = SysExit.EX_IOERR if ret < 0 else SysExit.EX_OK

        elif mode is Mode.DETACH:
            ret = DfuUtil.dfu_root.detach(1000)
            if int_(ret) < 0:
                logger.warning("can't detach")
                # allow combination with final_reset
                ret = 0
        else:
            logger.warning(f"Unsupported mode: {mode}")
            ret = SysExit.EX_SOFTWARE

        if ret == 0 and final_reset:
            if int_(ret) < 0:
                # Even if detach failed,
                # just carry on to leave the device in a known state
                logger.warning("can't detach")
            logger.info("Resetting USB to switch back to Run-Time mode")
            ret = DfuUtil.dfu_root.dev.reset()
            if ret < 0 and ret != LIBUSB_ERROR_NOT_FOUND:
                logger.warning(f"error resetting after download: {ret}")
                ret = SysExit.EX_IOERR
            else:
                ret = SysExit.EX_OK

        DfuUtil.dfu_root.dev = None
        disconnect_devices()
        sys.exit(ret)


    # probe
    def probe():
        nonlocal ctx
        nonlocal runtime_vendor, runtime_product

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
                    status.bwPollTimeout = 0
                    status.bState = dfu.State.APP_IDLE
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

            if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
                logger.info("Device really in Run-Time Mode, send DFU detach request")
                if int_(DfuUtil.dfu_root.detach(1000)) < 0:
                    logger.error(f"error detaching")
                if DfuUtil.dfu_root.func_dfu.bmAttributes & BmAttributes.USB_DFU_WILL_DETACH:
                    logger.info("Device will detach and reattach...")
                else:
                    logger.info("Resetting USB...")
                    try:
                        ret = DfuUtil.dfu_root.dev.reset()
                    except usb.core.USBError as e:
                        raise _IOError(f"error resetting after detach: {e}") from e
            elif status.bState == dfu.State.DFU_ERROR:
                logger.info("dfuERROR, clearing status")
                try:
                    DfuUtil.dfu_root.clear_status()
                except usb.core.USBError as e:
                    raise _IOError("error clear_status") from e
                # fall through
            else:
                logger.warning(
                    f"Device already in DFU mode? "
                    f"(bState={status.bState} {status.bStatus.to_string()})"
                )
                try:
                    usb.util.claim_interface(DfuUtil.dfu_root.dev,
                                             DfuUtil.dfu_root.interface)
                except usb.core.USBError as e:
                    logger.warning(e)
                # goto dfu_state
                dfu_state()

            try:
                usb.util.claim_interface(DfuUtil.dfu_root.dev,
                                         DfuUtil.dfu_root.interface)
            except usb.core.USBError as e:
                logger.warning(e)
            DfuUtil.dfu_root.dev = None

            # keeping handles open might prevent re-enumeration
            disconnect_devices()

            if mode is Mode.DETACH:
                sys.exit(SysExit.EX_OK)

            milli_sleep(detach_delay * 1000)

            # Change match vendor and product to impossible values to force
            # only DFU mode matches in the following probe

            DfuUtil.match_vendor, DfuUtil.match_product = 0x10000, 0x10000

            probe_devices(ctx)

            if DfuUtil.dfu_root is None:
                raise _IOError("Lost device after RESET?")
            elif DfuUtil.dfu_root.next is not None:
                raise _IOError(
                    "More than one DFU capable USB device found! "
                    "Try `--list' and specify the serial number "
                    "or disconnect all but one device"
                )

            # Check for DFU mode device
            if DfuUtil.dfu_root.flags | dfu.IFF.DFU:
                raise ProtocolError("Device is not in DFU mode")

            logger.info("Opening DFU USB Device...")
            if DfuUtil.dfu_root.dev is None:
                raise _IOError("Cannot open device")

        else:
            # we're already in DFU mode,
            # so we can skip the detach/reset procedure
            # If a match vendor/product was specified, use that as the runtime
            # vendor/product, otherwise use the DFU mode vendor/product
            runtime_vendor = (DfuUtil.dfu_root.vendor
                              if DfuUtil.match_vendor < 0
                              else DfuUtil.match_vendor)
            runtime_product = (DfuUtil.dfu_root.product
                               if DfuUtil.match_product < 0
                               else DfuUtil.match_product)

        dfu_state()

    probe()


if __name__ == '__main__':
    main()

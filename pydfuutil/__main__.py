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
import errno
import importlib.metadata
import logging
import os
import re
import sys
from enum import Enum
from typing import Literal, Optional

import usb.core

from pydfuutil import dfu
from pydfuutil import dfu_file
from pydfuutil import dfu_load
from pydfuutil import dfuse
from pydfuutil import quirks
from pydfuutil import usb_dfu
from pydfuutil.exceptions import Errx, MissUseError, CompatibilityError, except_and_safe_exit
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep

try:
    __version__ = importlib.metadata.version("pydfuutil")
except importlib.metadata.PackageNotFoundError:
    __version__ = 'UNKNOWN'

VERSION = (f"pydfuutil {__version__}\n\n"
           f"2023 Yaroshenko Dmytro (https://github.com/o-murphy)\n")

usb_logger = logging.getLogger('usb')
MAX_DESC_STR_LEN = 253
HAVE_GET_PAGESIZE = sys.platform != 'win32'


def atoi(s: str) -> int:
    """
    Regular expression to match the integer part of the string
    :param s: input
    :return: Return 0 if no integer is found
    """
    # match hex
    match = re.match(r'^\dx([\da-fA-F]+)', s)
    if match:
        result = int(match.group(1), 16)
        return result

    # match tens
    match = re.match(r'^\s*([-+]?\d+)', s)
    if match:
        result = int(match.group(1))
        return result

    return 0


def usb_path2devnum(path: str) -> int:
    """parse the dev bus/port"""

    parts = path.split('-')
    # bus_number = int(parts[0])
    # port_numbers, config_interface = parts[1].split(':')
    port_numbers, _ = parts[1].split(':')
    port_numbers = list(map(int, port_numbers.split('.')))
    # config, interface = map(int, config_interface.split('.'))

    devnum = 0
    for port in port_numbers:
        devnum <<= 4
        devnum += port
    return devnum


def find_dfu_if(dev: usb.core.Device) -> list[dfu.DfuIf]:
    """
    Find DFU interface for a given USB device.
    :param dev: The USB device.
    :return: 0 if no DFU interface is found, or the result of the handler function.
    """
    configs = dev.configurations()  # .desc

    for cfg in configs:
        for intf in cfg:
            if intf.bInterfaceClass == 0xfe and intf.bInterfaceSubClass == 1:
                dfu_if = dfu.DfuIf(
                    vendor=dev.idVendor,
                    product=dev.idProduct,
                    bcdDevice=dev.bcdDevice,
                    configuration=cfg.bConfigurationValue,
                    interface=intf.bInterfaceNumber,
                    altsetting=intf.bAlternateSetting,
                    alt_name="",
                    bus=dev.bus,
                    devnum=dev.address,
                    path=dev.address,
                    flags=0,
                    count=0,
                    dev=dev
                )
                yield dfu_if


def get_first_dfu_if(dev: usb.core.Device) -> dfu.DfuIf:
    """
    Fills in dif with the first found DFU interface.
    :param dev: the DFU capable USB device
    :return: 0 if no DFU interface is found, 1 otherwise.
    """
    if dfu_if := next((i for i in find_dfu_if(dev) if i is not None), None):
        return dfu_if
    raise Errx("Cannot open device")


def _check_match_cb(dif: dfu.DfuIf, other: dfu.DfuIf):
    if other.flags & dfu.IFF.IFACE and dif.interface != other.interface:
        return 0
    if other.flags & dfu.IFF.ALT and dif.altsetting != other.altsetting:
        return 0
    return 1


def get_matching_dfu_if(dif: dfu.DfuIf) -> int:
    """
    Fills in dif from the matching DFU interface/altsetting.
    :param dif: The DFU interface struct.
    :return: 0 if no matching interface/altsetting is found, 1 otherwise.
    """
    for dfu_if in find_dfu_if(dif.dev):
        if _check_match_cb(dif, dfu_if):
            # Copy everything except the device handle.
            # This depends heavily on this member being last!
            dfu_if.__dict__.update(
                (k, getattr(dif, k)) for k in dif.__dict__
                if k != 'dev'
            )
            return 1
    return 0


def count_matching_dfu_if(dif: dfu.DfuIf) -> int:
    """
    Count matching DFU interfaces/altsettings.
    :param dif: The DFU interface struct.
    :return: The number of matching DFU interfaces/altsettings.
    """
    dif.count = 0
    for dfu_if in find_dfu_if(dif.dev):
        if _check_match_cb(dif, dfu_if):
            dif.count += 1

    return dif.count


def get_alt_name(dfu_if: dfu.DfuIf) -> [int, str]:
    """
    Retrieves alternate interface name string.

    :param dfu_if: The DFU interface struct.
    :return: The alternate interface name string or a negative integer on error.
    """
    dev = dfu_if.dev
    cfg = dev.get_active_configuration()
    intf: usb.core.Interface = cfg[(dfu_if.interface, dfu_if.altsetting)]

    alt_name_str_idx = intf.iInterface
    if not alt_name_str_idx:
        return -1
    try:
        return usb.util.get_string(dev, alt_name_str_idx)
    except usb.core.USBError:
        return -1


def print_dfu_if(dfu_if: dfu.DfuIf) -> int:
    """
    Print DFU interface information.
    :param dfu_if: The DFU interface struct.
    :return: Always returns 0.
    """
    name = get_alt_name(dfu_if) or "UNDEFINED"
    logger.info(f"Found {'DFU' if dfu_if.flags & dfu.IFF.DFU else 'Runtime'}: "
                f"[{dfu_if.vendor:04x}:{dfu_if.product:04x}] "
                f"devnum={dfu_if.devnum}, cfg={dfu_if.configuration}, "
                f"intf={dfu_if.interface}, alt={dfu_if.altsetting}, "
                f"name=\"{name}\"")
    if sys.platform != "win32":
        logger.debug(get_device_path(dfu_if.dev))
    return 0


def list_dfu_interfaces(ctx: list[usb.core.Device]) -> int:
    """
    Walk the device tree and print out DFU devices.
    :param ctx: libusb context
    :return: 0 on success.
    """
    for dev in ctx:
        for dfu_if in find_dfu_if(dev):
            print_dfu_if(dfu_if)
        usb.util.dispose_resources(dev)
    return 0


def alt_by_name(dfu_if: dfu.DfuIf, v: str) -> int:
    """
    Find alternate setting by name.
    :param dfu_if: The DFU interface struct.
    :param v: The name of the alternate setting.
    :return: The alternate setting number if found, 0 otherwise.
    """
    name = get_alt_name(dfu_if)
    if name is None:
        return 0
    if name != v:
        return 0
    # Return altsetting+1 so that we can
    # use return value 0 to indicate not found
    return dfu_if.altsetting + 1


def count_dfu_interfaces(dev: usb.core.Device) -> int:
    """
    Count DFU interfaces within a single device.
    :param dev: The USB device.
    :return: The number of DFU interfaces found.
    """
    return sum(1 for _ in find_dfu_if(dev))


def iterate_dfu_devices(ctx: list[usb.core.Device], dif: dfu.DfuIf) -> list[usb.core.Device]:
    """
    Iterate over all matching DFU capable devices within the system.
    :param ctx: The USB context.
    :param dif: The DFU interface.
    :return: List of matching DFU capable devices.
    """
    retval = []
    for dev in ctx:
        if dif:
            if ((dif.flags & dfu.IFF.DEVNUM)
                    and (dev.bus != dif.bus or dev.address != dif.devnum)):
                continue
            if (dif.flags & dfu.IFF.VENDOR) and dev.idVendor != dif.vendor:
                continue
            if (dif.flags & dfu.IFF.PRODUCT) and dev.idProduct != dif.product:
                continue
        if count_dfu_interfaces(dev):
            retval.append(dev)
        usb.util.dispose_resources(dev)
    return retval


def parse_vid_pid(string: str) -> tuple[int, int]:
    """
    Parse a string containing vendor and product IDs in hexadecimal format.
    :param string: The string containing vendor and product IDs separated by ':'.
    :return: A tuple containing the vendor and product IDs.
    """
    vendor, product = 0, 0
    try:
        vendor_str, product_str = string.split(':')
        if vendor_str:
            vendor = int(vendor_str, 16)
        if product_str:
            product = int(product_str, 16)
    except (ValueError, TypeError, AttributeError):
        pass
    return vendor, product


def get_device_path(dev: usb.core.Device) -> str:
    """
    Get device path
    :param dev:
    :return str:
    """
    # Retrieve bus and device numbers
    bus_number = dev.bus
    device_number = dev.address
    parent = dev.parent
    # Retrieve port numbers
    port_numbers = [device_number]
    while parent is not None:
        port_numbers.insert(0, parent.port_number)
        parent = parent.parent

    # Construct device path
    device_path = f"{bus_number}-{port_numbers.pop(0)}"
    for port in port_numbers:
        device_path += f".{port}"

    # Append configuration and interface numbers
    cfg = dev.get_active_configuration()
    device_path += f":{cfg.bConfigurationValue}.{cfg[(0, 0)].bInterfaceNumber}"

    return device_path


# FIXME: maybe useless if pyusb uses?
def resolve_device_path(dif: dfu.DfuIf) -> int:
    """
    :param dif: DfuIf instance
    """
    try:
        if sys.platform == "win32":
            raise SystemError("USB device paths are not supported by Windows")
        res: int = usb_path2devnum(dif.path)
        if res < 0:
            return -errno.EINVAL
        if not res:
            return 0

        dif.bus = atoi(dif.path)
        dif.devnum = res
        dif.flags |= dfu.IFF.DEVNUM
        logger.debug(f"DIF PATH: {dif.path}: {dif.bus}")
        return res
    except SystemError as err:
        logger.error(err)
    except Exception as err:
        logger.error("USB device paths are not supported by this dfu-util")
        logger.debug(err)
    raise Errx


def find_descriptor(desc_list: list, desc_type: int, desc_index: int,
                    res_buf: bytes) -> int:
    """
    Look for a descriptor in a concatenated descriptor list
    Will return desc_index'th match of given descriptor type
    :param desc_list: The concatenated descriptor list.
    :param desc_type: The type of descriptor to search for.
    :param desc_index: The index of the descriptor to find.
    :param res_buf: The buffer to store the found descriptor.
    :return: length of found descriptor, limited to res_size
    """

    p: int = 0
    hit: int = 0
    res_buf = bytearray(res_buf)

    while p + 1 < len(desc_list):
        desc_len = int(desc_list[p])

        if desc_len == 0:
            logger.error("Invalid descriptor list")
            return -1

        if desc_list[p + 1] == desc_type and hit == desc_index:
            desc_len = min(desc_len, len(res_buf))
            if p + desc_len > len(desc_list):
                desc_len = len(desc_list) - p
            res_buf[:desc_len] = desc_list[p:p + desc_len]
            return desc_len

        if desc_list[p + 1] == desc_type:
            hit += 1

        p += int(desc_list[p])

    return 0


def usb_get_any_descriptor(dev: usb.core.Device,
                           desc_type: int,
                           desc_index: int,
                           res_buf: bytes) -> int:
    """
    Look for a descriptor in the active configuration.
    Will also find extra descriptors which
    are normally not returned by the standard libusb_get_descriptor().

    :param dev: The device handle.
    :param desc_type: The descriptor type.
    :param desc_index: The descriptor index.
    :param res_buf: The buffer to store the descriptor.
    :return: The length of the found descriptor.
    """

    res_buf = bytearray(res_buf)
    # Get the total length of the configuration descriptors
    config = dev.get_active_configuration()
    conf_len = config.wTotalLength

    # Suck in the configuration descriptor list from device

    c_buf = usb.control.get_descriptor(dev, usb.DT_CONFIG_SIZE, usb.DT_CONFIG, 0).tobytes()

    # c_buf = dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
    #                          (usb.util.DESC_TYPE_CONFIG << 8) | 0, 0, conflen)

    if len(c_buf) < conf_len:
        logger.warning(
            f"failed to retrieve complete configuration descriptor, got {len(c_buf)}/{conf_len}"
        )
        conf_len = len(c_buf)

    # Search through the configuration descriptor list
    ret = find_descriptor(c_buf, desc_type, desc_index, res_buf)
    if ret > 1:
        logger.debug("Found descriptor in complete configuration descriptor list")
        return ret

    # Finally try to retrieve it requesting the device directly
    # This is not supported on all devices for non-standard types
    # return dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
    #                          (desc_type << 8) | desc_index, 0, resbuf)
    return usb.control.get_descriptor(dev, usb.DT_CONFIG_SIZE, desc_type, desc_index).tobytes()


# pylint: disable=invalid-name
def get_cached_extra_descriptor(dfu_if: dfu.DfuIf,
                                desc_type: int,
                                desc_index: int,
                                res_buf: bytes) -> int:
    """
    Get cached extra descriptor from libusb for an interface.
    :param dfu_if: DFU interface.
    :param desc_type: The descriptor type.
    :param desc_index: The descriptor index.
    :param res_buf: The buffer to store the descriptor.
    :return: The length of the found descriptor.
    """

    dev = dfu_if.dev
    bConfValue = dfu_if.configuration
    intf = dfu_if.interface

    cfg = dev.configurations()[bConfValue - 1]
    try:
        intf_desc = cfg.interfaces()[intf]
    except usb.core.USBError as e:
        if e.errno == errno.ENOENT:
            logger.error("Device is unconfigured")
        else:
            logger.error("Failed to get configuration descriptor")
        return -1

    ret = -1

    for altsetting in intf_desc:
        extra = altsetting.extra
        extra_len = altsetting.extra_length

        if extra_len > 1:
            ret = find_descriptor(extra, desc_type, desc_index, res_buf)

        if ret > 1:
            break

    if ret < 2:
        logger.debug("Did not find cached descriptor")

    return ret


class Mode(Enum):
    """dfu-util cli mode"""
    NONE = 0
    VERSION = 1
    LIST = 2
    DETACH = 3
    UPLOAD = 4
    DOWNLOAD = 5


def cpu_to_le16(value: int) -> bytes:
    """Convert int to uint16le"""
    return value.to_bytes(2, byteorder='little')


def le16_to_cpu(data: bytes) -> int:
    """Convert uint16le to int"""
    return int.from_bytes(data, byteorder='little')


def int_(value: [int, bytes, bytearray],
         order: Optional[Literal["little", "big"]] = 'little') -> int:
    """coerce value to int"""
    if isinstance(value, int):
        return value
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(value, order)
    raise TypeError("Unsupported type")


def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add cli options"""
    parser.add_argument("-V", "--version", action="version", version=VERSION,
                        help="Print the version number")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print verbose debug statements")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List the currently attached DFU capable USB devices")
    parser.add_argument("-e", "--detach", action="store_true",
                        help="Detach the currently attached DFU capable USB devices")
    # TODO: Not implemented
    # parser.add_argument("-E", "--detach-delay", action="store",
    #                     type=int, default=1, metavar="<seconds>",
    #                     help="Time to wait before reopening a device after detach")
    parser.add_argument("-d", "--device", metavar="<deviceID>:<productID>",
                        help="Specify Vendor/Product ID of DFU device")
    # TODO: Not implemented
    # parser.add_argument("-n", "--devnum", metavar="<dnum>",
    #                     help="Match given device number (devnum from --list)")
    parser.add_argument("-p", "--path", metavar="<bus-port. ... .port>",
                        help="Specify path to DFU device")
    parser.add_argument("-c", "--cfg", metavar="<config_nr>",
                        help="Specify the Configuration of DFU device")
    parser.add_argument("-i", "--intf", metavar="<intf_nr>",
                        help="Specify the DFU Interface number")
    # TODO: Not implemented
    # parser.add_argument("-S", "--serial", metavar="<serial_string>[,<serial_string_dfu>]",
    #                     help="Specify the DFU Interface number")
    parser.add_argument("-a", "--alt", metavar="<alt>",
                        help="Specify the Altsetting of the DFU Interface")
    parser.add_argument("-t", "--transfer-size", metavar="<size>",
                        help="Specify the number of bytes per USB Transfer")
    parser.add_argument("-U", "--upload", metavar="<file>",
                        help="Read firmware from device into <file>")
    # TODO: Not implemented
    # parser.add_argument("-Z", "--upload-size", metavar="<bytes>",
    #                     help="Specify the expected upload size in bytes")
    parser.add_argument("-D", "--download", metavar="<file>",
                        help="Write firmware from <file> into device")
    parser.add_argument("-R", "--reset", action="store_true",
                        help="Issue USB Reset signalling once we're finished")
    #  TODO: Not implemented
    # parser.add_argument("-w", "--wait", action="store_true",
    #                     help="Wait for device to appear")
    parser.add_argument("-s", "--dfuse-address", metavar="<address>",
                        help="ST DfuSe mode, specify target address "
                             "for raw file download or upload. "
                             "Not applicable for DfuSe file (.dfu) downloads")
    #
    #                         ST DfuSe mode string, specifying target
    #                                 address for raw file download or upload (not
    #                                 applicable for DfuSe file (.dfu) downloads).
    #                                 Add more DfuSe options separated with ':'
    #                 leave           Leave DFU mode (jump to application)
    #                 mass-erase      Erase the whole device (requires "force")
    #                 unprotect       Erase read protected device (requires "force")
    #                 will-reset      Expect device to reset (e.g. option bytes write)
    #                 force           You really know what you are doing!
    #                 <length>        Length of firmware to upload from device
    #
    parser.add_argument("-y", "--yes-to-all", action="store_true",
                        help="Say yes to all prompts")


@except_and_safe_exit(logger)
def main() -> None:
    """Cli entry point"""

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog="pydfuutil",
        description="Python implementation of DFU-Util tools"
    )
    add_cli_options(parser)

    print(f"v{__version__}")
    # parse options
    args = parser.parse_args()
    dif: dfu.DfuIf = dfu.DfuIf()
    file = dfu_file.DfuFile(None)
    mode = Mode.NONE
    device_id_filter = None
    alt_name = None
    transfer_size = 0
    dfuse_device = 0
    dfuse_options = None
    final_reset = 0

    func_dfu_rt = usb_dfu.FuncDescriptor()
    func_dfu = usb_dfu.FuncDescriptor()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        usb_logger.setLevel(logging.DEBUG)

    if args.list:
        mode = Mode.LIST

    if args.detach:
        mode = Mode.DETACH

    if args.device:
        device_id_filter = args.device

    if args.path:
        dif.path = args.path
        dif.flags |= dfu.IFF.PATH
        if ret := resolve_device_path(dif):
            raise MissUseError(f"unable to parse {args.path}")
        if not ret:
            raise Errx(f"cannot find {args.path}")

    if args.cfg:
        dif.configuration = atoi(args.cfg)
        dif.flags |= dfu.IFF.CONFIG

    if args.intf:
        dif.interface = atoi(args.intf)
        dif.flags |= dfu.IFF.IFACE

    if args.alt:
        altsetting = int(args.alt, 0)
        if args.alt.isdigit() and altsetting:
            dif.altsetting = altsetting
        else:
            alt_name = args.alt
        dif.flags |= dfu.IFF.ALT

    if args.transfer_size:
        transfer_size = atoi(args.transfer_size)

    if args.upload:
        mode = Mode.UPLOAD
        file.name = args.upload

    if args.download:
        mode = Mode.DOWNLOAD
        file.name = args.download

    if args.reset:
        final_reset = 1

    if args.dfuse_address:
        dfuse_options = args.dfuse_address

    if mode == Mode.NONE:
        logger.error("You need to specify one of -D or -U\n\n")
        parser.print_help()
        raise MissUseError

    if device_id_filter:
        dif.vendor, dif.product = parse_vid_pid(device_id_filter)
        logger.info(f"Filter on VID = 0x{dif.vendor:04X} PID = 0x{dif.product:04X}\n")
        if dif.vendor:
            dif.flags |= dfu.IFF.VENDOR
        if dif.product:
            dif.flags |= dfu.IFF.PRODUCT

    apply_all = args.yes_to_all

    # libusb init
    libusb_ctx = list(usb.core.find(find_all=True, **dif.device_ids))

    if mode == Mode.LIST:
        logger.debug(mode)
        list_dfu_interfaces(libusb_ctx)
        sys.exit(0)

    dfu.init(5000)

    dfu_capable = iterate_dfu_devices(libusb_ctx, dif)

    if len(dfu_capable) == 0:
        raise Errx("No DFU capable USB device found")
    elif len(dfu_capable) > 1:
        # We cannot safely support more than one DFU capable device
        # with same vendor/product ID, since during DFU we need to do
        # a USB bus reset, after which the target device will get a
        # new address */
        raise CompatibilityError("More than one DFU capable USB device found, "
                              "you might try `--list' and then disconnect all but one "
                              "device")

    # get_first_dfu_device
    if not (dev := dfu_capable[0]):
        raise CompatibilityError("Can't get DFU capable USB device")

    # We have exactly one device. Its libusb_device is now in dif->dev
    logger.info("Opening DFU capable USB device... ")

    _rt_dif: dfu.DfuIf = get_first_dfu_if(dev)

    logger.info(f"ID 0x{_rt_dif.vendor:04X}:0x{_rt_dif.product:04X}")

    _quirks = quirks.get_quirks(_rt_dif.vendor, _rt_dif.product, _rt_dif.bcdDevice)

    # Obtain run-time DFU functional descriptor without asking device
    # E.g. Free runner does not like to be requested at this point

    ret = get_cached_extra_descriptor(_rt_dif, usb_dfu.USB_DT_DFU,
                                      0, cpu_to_le16(func_dfu_rt.bcdDFUVersion))
    if ret == 7:
        logger.info("Deducing device DFU version from functional descriptor "
                    "length")
        func_dfu_rt.bcdDFUVersion = 0x0100
    elif ret < 9:
        logger.warning("Can not find cached DFU functional descriptor")
        logger.warning("Assuming DFU version 1.0")
        func_dfu_rt.bcdDFUVersion = 0x0100

    logger.info(f"Run-time device DFU version 0x{func_dfu_rt.bcdDFUVersion:04X}")

    # Transition from run-Time mode to DFU mode

    def check_status(dfu_if: dfu.DfuIf):
        # status_again
        logger.debug('Status again')
        _log_msg = "Determining device status: "
        if int(status_ := dfu_if.get_status()) < 0:
            raise Errx(f"{_log_msg}error get_status")
        logger.info(f"{_log_msg}state = {status_.bState.to_string()}, "
                    f"status = {status_.bStatus}")
        if not _quirks & quirks.QUIRK.POLLTIMEOUT:
            milli_sleep(status_.bwPollTimeout)
        return status_

    if not _rt_dif.flags & dfu.IFF.DFU:
        # In the 'first round' during runtime mode, there can only be one
        # DFU Interface descriptor according to the DFU Spec.
        # Note: future warning: check if the selected device really has only one

        logger.info("Claiming USB DFU Runtime Interface...")
        try:
            usb.util.claim_interface(_rt_dif.dev, _rt_dif.interface)
        except usb.core.USBError:
            raise Errx(f"Cannot claim interface {_rt_dif.interface}")

        try:
            _rt_dif.dev.set_interface_altsetting(_rt_dif.interface, 0)
        except usb.core.USBError:
            raise Errx("Cannot set alt interface zero")

        status = check_status(_rt_dif)

        if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
            logger.info("Device really in Runtime Mode, send DFU "
                        "detach request...")

            if int_(_rt_dif.detach(1000)) < 0:
                raise Errx("error detaching")

            if func_dfu_rt.bmAttributes & usb_dfu.BmAttributes.USB_DFU_WILL_DETACH:
                logger.info("Device will detach and reattach...")
            else:
                logger.info("Resetting USB...\n")
                try:
                    _rt_dif.dev.reset()
                except usb.core.USBError:
                    logger.error("error resetting after detach")
            milli_sleep(2000)
        elif status.bState == dfu.State.DFU_ERROR:
            logger.error("dfuERROR, clearing status")
            if dfu._clear_status(_rt_dif.dev, _rt_dif.interface) < 0:
                raise Errx("error detaching")
        else:
            logger.info("Runtime device already in DFU state ?!?")

        usb.util.release_interface(_rt_dif.dev, _rt_dif.interface)
        usb.util.dispose_resources(_rt_dif.dev)

        if mode == Mode.DETACH:
            usb.util.release_interface(_rt_dif.dev, _rt_dif.interface)
            usb.util.dispose_resources(_rt_dif.dev)
            sys.exit(0)

        if dif.flags & dfu.IFF.PATH:
            ret = resolve_device_path(dif)
            if not ret:
                raise Errx("Cannot resolve path after RESET?")
            if int_(ret) < 0:
                raise Errx(f"internal error: cannot re-parse {dif.path}")

        dfu_capable = iterate_dfu_devices(libusb_ctx, dif)
        if len(dfu_capable) == 0:
            raise Errx("Lost device after RESET?")
        elif len(dfu_capable) > 1:
            raise Errx("More than one DFU capable USB "
                               "device found, you might try `--list' and "
                               "then disconnect all but one device")

    # get first detached dfu if
    dif: dfu.DfuIf = get_first_dfu_if(dev)

    logger.debug(dif)
    logger.info("Opening DFU USB Device...")

    # we're already in DFU mode, so we can skip the detach/reset procedure

    logger.debug('Dfu state...')  # dfustate

    if alt_name:
        n = next((alt_by_name(dfu_if, alt_name) for dfu_if in find_dfu_if(dev)), None)
        if not n:
            raise Errx(f"No such Alternate Setting: {alt_name}")
        if n < 0:
            raise Errx(f"Error {n} in name lookup")
        dif.altsetting = n - 1

    if (num_ifs := count_matching_dfu_if(dif)) < 0:
        raise Errx("No matching DFU Interface after RESET?!?")
    elif num_ifs > 1:
        logger.warning("Detected interfaces after DFU transition")
        list_dfu_interfaces(libusb_ctx)
        raise Errx(f"We have {num_ifs} DFU Interfaces/Altsettings,"
                           " you have to specify one via --intf / --alt"
                           " options")

    if not get_matching_dfu_if(dif):
        raise Errx("Can't find the matching DFU interface/altsetting")

    print_dfu_if(dif)
    if (active_alt_name := get_alt_name(dif)) and len(active_alt_name) > 0:
        dif.alt_name = active_alt_name
    else:
        dif.alt_name = None

    # # Note: uncomment on need
    # logger.info(f"Setting Configuration {dif.configuration}...")
    # try:
    #     dif.dev.set_configuration(dif.configuration)
    # except usb.core.USBError as e:
    #     raise Errx("Cannot set configuration")

    logger.info("Claiming USB DFU Interface...")
    try:
        usb.util.claim_interface(dif.dev, dif.interface)
    except usb.core.USBError:
        raise Errx("Cannot claim interface")

    logger.info(f"Setting Alternate Setting {dif.altsetting} ...\n")
    try:
        dif.dev.set_interface_altsetting(dif.interface, dif.altsetting)
    except usb.core.USBError:
        raise Errx("Cannot set alternate interface")

    status = check_status(dif)
    while status.bState != dfu.State.DFU_IDLE:

        if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
            raise Errx("Device still in Runtime Mode!")

        elif status.bState == dfu.State.DFU_ERROR:
            logger.error("dfuERROR, clearing status")
            if dfu._clear_status(dif.dev, dif.interface) < 0:
                raise Errx("error clear_status")

            status = check_status(dif)

        elif status.bState == (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_UPLOAD_IDLE):
            logger.warning("aborting previous incomplete transfer")
            if dif.abort() < 0:
                raise Errx("can't send DFU_ABORT")

            status = check_status(dif)

        elif status.bState == dfu.State.DFU_IDLE:
            logger.info("dfuIDLE, continuing")
            break

    if status.bStatus != dfu.Status.OK:
        logger.warning(f"DFU Status: {status.bStatus.to_string()}")

        # Clear our status & try again.
        dfu._clear_status(dif.dev, dif.interface)
        _ = int(status := dif.get_status())
        if status.bStatus != dfu.Status.OK:
            raise Errx(f"{status.bStatus}")
        if not _quirks & quirks.QUIRK.POLLTIMEOUT:
            milli_sleep(status.bwPollTimeout)

    logger.debug(f"State: {status.bState.to_string()}, "
                 f"Status: {status.bStatus.to_string()} Continue...")

    # Get the DFU mode DFU functional descriptor
    # If it is not found cached, we will request it from the device

    ret = get_cached_extra_descriptor(dif, usb_dfu.USB_DT_DFU,
                                      0, cpu_to_le16(func_dfu.bcdDFUVersion))
    if ret < 7:
        logger.error("obtaining cached DFU functional descriptor")
        ret = usb_get_any_descriptor(
            dif.dev, usb_dfu.USB_DT_DFU, 0,
            cpu_to_le16(func_dfu_rt.bcdDFUVersion)
        )
        ret = int_(ret)
    if ret == 7:
        logger.info("Deducing device DFU version from functional descriptor length")
        func_dfu.bcdDFUVersion = 0x0100
    elif ret < 9:
        logger.error("Error obtaining DFU functional descriptor")
        logger.info("Please report this as a bug!")
        logger.warning("Assuming DFU version 1.0")
        func_dfu.bcdDFUVersion = 0x0100
        logger.warning("Warning: Transfer size can not be detected")
        func_dfu.wTransferSize = 0

    if _quirks & quirks.QUIRK.FORCE_DFU11:
        func_dfu.bcdDFUVersion = 0x0110

    logger.info(f"DFU mode device DFU version  0x{func_dfu.bcdDFUVersion:04X}")

    if func_dfu.bcdDFUVersion == 0x11a:
        dfuse_device = 1

    # If not overridden by the user
    # FIXME: can't got how the total size specified
    if transfer_size:
        logger.info(f"Device returned transfer size {transfer_size}")
    else:
        raise Errx("Transfer size must be specified")

    # autotools lie when cross-compiling for Windows using mingw32/64
    if HAVE_GET_PAGESIZE:
        # limitation of Linux usbdevio
        page_size = os.sysconf(os.sysconf_names['SC_PAGE_SIZE'])
        if transfer_size > page_size:
            transfer_size = page_size
            logger.info(f"Limited transfer size to {transfer_size}")

    # DFU specification
    # if dif.dev:  # strange think, unreachable
    #     raise Errx(f"Failed to get device descriptor")

    # pylint: disable=no-member
    if transfer_size < dif.dev.bMaxPacketSize0:
        logger.info(f"Adjusted transfer size to {transfer_size}")

    if mode == Mode.UPLOAD:
        # open for "exclusive" writing in a portable way
        try:
            file_mode = "ab"
            if os.path.isfile(file.name) and os.path.getsize(file.name) != 0:
                # ask to overwrite file that exist
                if not apply_all:
                    _y = input(f"{file.name} File exists, print `yes` to overwrite: ")
                    if not _y.lower() in ('y', 'yes'):
                        raise Errx(f"{file.name}: File exists")
                file_mode = 'wb'

            with open(file.name, file_mode) as file.file_p:

                if dfuse_device or dfuse_options:
                    if dfuse.do_upload(dif, transfer_size, file, dfuse_options) < 0:
                        raise Errx
                else:
                    if dfu_load.do_upload(dif, transfer_size, file) < 0:
                        raise Errx

        except OSError as e:
            raise Errx(e)

    elif mode == Mode.DOWNLOAD:
        try:
            # Open file for reading in binary mode
            with open(file.name, "rb") as file_p:
                if not file_p:
                    raise Errx(f"Error: Failed to open {file.name}")

                # Parse DFU suffix
                # ret = dfu_file.parse_dfu_suffix(file)
                ret = file.parse_dfu_suffix()
                if ret < 0:
                    raise Errx
                elif ret == 0:
                    logger.warning("File has no DFU suffix")
                elif file.bcdDFU not in (0x0100, 0x011a):
                    raise Errx(f"Unsupported DFU file revision 0x{file.bcdDFU:04x}")

                # Check vendor ID
                if file.idVendor not in (0xffff, dif.vendor):
                    logger.warning(f"Warning: File vendor ID 0x{file.idVendor:04x} "
                                   f"does not match device 0x{dif.vendor:04x}")

                # Check product ID
                if file.idProduct not in (0xffff, dif.product):
                    logger.warning(f"File product ID 0x{file.idProduct:04x} "
                                   f"does not match device 0x{dif.product:04x}")

                # Perform download based on conditions
                if dfuse_device or dfuse_options or file.bcdDFU == 0x011a:
                    if dfuse.do_download(dif, transfer_size, file, dfuse_options) < 0:
                        raise Errx
                else:
                    if dfu_load.do_dnload(dif, transfer_size, file, _quirks) < 0:
                        raise Errx

        except OSError as e:
            raise Errx(e)

    else:
        raise Errx(f"Unsupported mode: {mode}")

    if final_reset:
        # if IntOrBytes(dfu.detach(dif.dev, dif.interface, 1000)) < 0:
        if int_(dif.detach(1000)) < 0:
            logger.error("can't detach")
        logger.info("Resetting USB to switch back to runtime mode")
        try:
            dif.dev.reset()
        except usb.core.USBError as e:
            logger.error("error resetting after download")
            logger.debug(e)

    usb.util.release_interface(dif.dev, dif.interface)
    usb.util.dispose_resources(dif.dev)


if __name__ == '__main__':
    main()

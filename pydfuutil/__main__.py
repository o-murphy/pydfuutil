"""
pydfuutil
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
Based on existing code of dfu-programmer-0.4
"""
import argparse
import errno
import logging
import os
import re
import sys
from enum import IntFlag
from typing import Any, Callable

import libusb_package
import usb.core
from usb.backend import libusb1

from pydfuutil import __version__, __copyright__, dfuse, dfu_load
from pydfuutil import dfu
from pydfuutil.dfu_file import DFUFile, parse_dfu_suffix
from pydfuutil.logger import get_logger
from pydfuutil.portable import milli_sleep
from pydfuutil.quirks import set_quirks, QUIRK_POLLTIMEOUT, QUIRK_FORCE_DFU11
from pydfuutil.usb_dfu import USB_DT_DFU, bmAttributes, USB_DFU_FUNC_DESCRIPTOR

logging.basicConfig(level=logging.DEBUG)
logging.propagate = False
logger = get_logger("dfu_util")
logger.setLevel(logging.INFO)
usb_logger = logging.getLogger('usb')
MAX_DESC_STR_LEN = 253
HAVE_GETPAGESIZE = not (sys.platform == 'win32')
VERBOSE = False

# TODO: not implemented yet
libusb1.get_backend(libusb_package.find_library)


def atoi(s: str) -> int:
    """
    Regular expression to match the integer part of the string
    :param s: input
    :return: Return 0 if no integer is found
    """
    match = re.match(r'^\s*([-+]?\d+)', s)

    if match:
        result = int(match.group(1))
        return result
    else:
        return 0


def usb_path2devnum(path: str) -> int:
    # TODO: wrong implementation
    parts = path.split('.')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    else:
        return 0


def find_dfu_if(dev: usb.core.Device,
                handler: Callable[[dfu.DfuIf, Any], Any] = None,
                v: Any = None) -> int:
    """
    Find DFU interface for a given USB device.

    :param dev: The USB device.
    :param handler: Callback function to handle the found DFU interface.
    :param v: Additional user-defined data for the callback function.
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

                if handler:
                    rc = handler(dfu_if, v)
                    if rc != 0:
                        return rc

    return 0


def _get_first_cb(dif: dfu.DfuIf, v: dfu.DfuIf) -> int:
    """
    Callback function to copy the first found DFU interface.

    :param dif: The DFU interface struct.
    :param v: The DFU interface struct to copy to.
    :return: 1 to indicate that the interface has been found.
    """
    # Copy everything except the device handle. This depends heavily on this member being last!
    v.__dict__.update((k, getattr(dif, k)) for k in dif.__dict__ if k != 'dev')

    # Return a value that makes find_dfu_if return immediately
    return 1


def _get_first_dfu_if(dif: dfu.DfuIf) -> int:
    """
    Fills in dif with the first found DFU interface.

    :param dif: The DFU interface struct.
    :return: 0 if no DFU interface is found, 1 otherwise.
    """
    return find_dfu_if(dif.dev, _get_first_cb, dif)


def _check_match_cb(dif: dfu.DfuIf, v: dfu.DfuIf) -> int:
    """
    Callback function to check matching DFU interfaces/altsettings.

    :param dif: The DFU interface struct.
    :param v: The DFU interface struct to match against.
    :return: 0 if no match is found, or the result of _get_first_cb.
    """
    if v.flags & dfu.Mode.IFF_IFACE and dif.interface != v.interface:
        return 0
    if v.flags & dfu.Mode.IFF_ALT and dif.altsetting != v.altsetting:
        return 0
    return _get_first_cb(dif, v)


def get_matching_dfu_if(dif: dfu.DfuIf) -> int:
    """
    Fills in dif from the matching DFU interface/altsetting.

    :param dif: The DFU interface struct.
    :return: 0 if no matching interface/altsetting is found, 1 otherwise.
    """
    return find_dfu_if(dif.dev, _check_match_cb, dif)


def _count_match_cb(dif: dfu.DfuIf, v: dfu.DfuIf) -> int:
    """
    Callback function to count matching DFU interfaces/altsettings.

    :param dif: The DFU interface struct.
    :param v: The DFU interface struct to match against.
    :return: Always returns 0.
    """
    if v.flags & dfu.Mode.IFF_IFACE and dif.interface != v.interface:
        return 0
    if v.flags & dfu.Mode.IFF_ALT and dif.altsetting != v.altsetting:
        return 0
    v.count += 1
    return 0


def count_matching_dfu_if(dif: dfu.DfuIf) -> int:
    """
    Count matching DFU interfaces/altsettings.

    :param dif: The DFU interface struct.
    :return: The number of matching DFU interfaces/altsettings.
    """
    dif.count = 0
    find_dfu_if(dif.dev, _count_match_cb, dif)
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

    if alt_name_str_idx:
        if not dfu_if.dev:
            try:
                dfu_if.dev = usb.util.find_descriptor(dev, find_all=True)
            except usb.core.USBError:
                dfu_if.dev = None

        if dfu_if.dev:
            try:
                return usb.util.get_string(dev, alt_name_str_idx)
            except usb.core.USBError:
                return -1

    return -1


def print_dfu_if(dfu_if: dfu.DfuIf, v: Any) -> int:
    """
    Print DFU interface information.

    :param dfu_if: The DFU interface struct.
    :param v: Unused (can be any value).
    :return: Always returns 0.
    """

    name: str = get_alt_name(dfu_if)
    if name is None:
        name = b"UNDEFINED"

    print(f"Found {'DFU' if dfu_if.flags & dfu.Mode.IFF_DFU else 'Runtime'}: "
          f"[{dfu_if.vendor:04x}:{dfu_if.product:04x}] devnum={dfu_if.devnum}, "
          f"cfg={dfu_if.configuration}, intf={dfu_if.interface}, "
          f"alt={dfu_if.altsetting}, name=\"{name}\"")

    return 0


def list_dfu_interfaces(ctx: list[usb.core.Device]) -> int:
    """
    Walk the device tree and print out DFU devices.

    :param dif: dfu.DfuIf
    :param ctx: libusb context
    :return: 0 on success.
    """

    for dev in ctx:
        find_dfu_if(dev, print_dfu_if, None)
        usb.util.dispose_resources(dev)
    return 0


def alt_by_name(dfu_if: dfu.DfuIf, v: bytes) -> int:
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
    """
    Return altsetting+1 so that we can use return value 0 to indicate
    "not found".
    """
    return dfu_if.altsetting + 1


def count_dfu_interfaces(dev: usb.core.Device) -> int:
    """
    Count DFU interfaces within a single device.

    :param dev: The USB device.
    :return: The number of DFU interfaces found.
    """
    num_found: int = 0

    def count_cb(dif, v):
        nonlocal num_found
        num_found += v
        return 0

    find_dfu_if(dev, count_cb, 1)
    return num_found


def iterate_dfu_devices(ctx: list[usb.core.Device], dif: dfu.DfuIf) -> list[usb.core.Device]:
    """
    Iterate over all matching DFU capable devices within the system.

    :param ctx: The USB context.
    :param dif: The DFU interface.
    :param action: The action to perform for each device.
    :param user: Additional user-defined data.
    :return: 0 on success, or an error code.
    """
    retval = []
    for dev in ctx:

        if dif and (dif.flags & dfu.Mode.IFF_DEVNUM) and (dev.bus != dif.bus or dev.address != dif.devnum):
            continue
        if dif and (dif.flags & dfu.Mode.IFF_VENDOR) and dev.idVendor != dif.vendor:
            continue
        if dif and (dif.flags & dfu.Mode.IFF_PRODUCT) and dev.idProduct != dif.product:
            continue
        if not count_dfu_interfaces(dev):
            continue
        usb.util.dispose_resources(dev)
        retval.append(dev)

    return retval


def found_dfu_device(dev: usb.core.Device, dif: dfu.DfuIf) -> int:
    """
    Save the DFU-capable device in dif.dev.

    :param dev: The USB device.
    :param dif: The DFU interface instance.
    :return: 1 always.
    """
    dif.dev = dev
    return 1


# def get_first_dfu_device(ctx: 'usb.core.Context', dif: dfu.DfuIf) -> int:
#     """
#     Find the first DFU-capable device and save it in dif.dev.
#
#     :param ctx: The USB context.
#     :param dif: The DFU interface struct.
#     :return: 0 on success, or an error code.
#     """
#     return iterate_dfu_devices(ctx, dif, found_dfu_device, dif)


def count_one_dfu_device(dev: usb.core.Device, user: list) -> int:
    """
    Count one DFU device.

    :param dev: The USB device.
    :param user: User-defined data (should be an integer pointer).
    :return: 0 always.
    """
    num = user
    num[0] += 1
    return 0


# def count_dfu_devices(ctx: list[usb.core.Device], dif: dfu.DfuIf) -> int:
#     """
#     Count the number of DFU devices connected to the USB context.
#
#     :param ctx: The libusb context.
#     :param dif: The DFU interface struct.
#     :return: The number of DFU devices found.
#     """
#     num_found = 0
#
#     iterate_dfu_devices(ctx, dif, count_one_dfu_device, num_found)
#     return num_found


def parse_vendprod(string: str) -> tuple[int, int]:
    """
    Parse a string containing vendor and product IDs in hexadecimal format.

    :param string: The string containing vendor and product IDs separated by ':'.
    :return: A tuple containing the vendor and product IDs.
    """
    vendor = 0
    product = 0

    vendor_str, product_str = string.split(':')

    if vendor_str:
        vendor = atoi(vendor_str)
    if product_str:
        product = atoi(product_str)

    return vendor, product


# TODO: maybe useless if pyusb uses
def resolve_device_path(dif: dfu.DfuIf) -> int:
    """
    :param dif: DfuIf instance
    """
    try:
        res: int = usb_path2devnum(dif.path)
        if res < 0:
            return -errno.EINVAL
        if not res:
            return 0

        dif.bus = atoi(dif.path)
        dif.devnum = res
        dif.flags |= dfu.Mode.IFF_DEVNUM
        return res
    except Exception as err:
        logger.error("USB device paths are not supported by this dfu-util.\n")
        sys.exit(1)


def find_descriptor(desc_list: list, desc_type: int, desc_index: int,
                    res_buf: bytearray) -> int:
    """
    Look for a descriptor in a concatenated descriptor list
    Will return desc_index'th match of given descriptor type

    :param desc_list: The concatenated descriptor list.
    :param desc_type: The type of descriptor to search for.
    :param desc_index: The index of the descriptor to find.
    :param res_buf: The buffer to store the found descriptor.
    :param res_size: The maximum size of the result buffer.
    :return: length of found descriptor, limited to res_size
    """

    p: int = 0
    hit: int = 0

    while p + 1 < len(desc_list):
        desclen = int(desc_list[p])

        if desclen == 0:
            logger.error("Invalid descriptor list")
            return -1

        if desc_list[p + 1] == desc_type and hit == desc_index:
            if desclen > len(res_buf):
                desclen = len(res_buf)
            if p + desclen > len(desc_list):
                desclen = len(desc_list) - p
            res_buf[:desclen] = desc_list[p:p + desclen]
            return desclen

        if desc_list[p + 1] == desc_type:
            hit += 1

        p += int(desc_list[p])

    return 0


def usb_get_any_descriptor(dev: usb.core.Device,
                           desc_type: int,
                           desc_index: int,
                           resbuf: bytearray) -> int:
    """
    Look for a descriptor in the active configuration.
    Will also find extra descriptors which are normally not returned by the standard libusb_get_descriptor().

    :param dev_handle: The device handle.
    :param desc_type: The descriptor type.
    :param desc_index: The descriptor index.
    :param resbuf: The buffer to store the descriptor.
    :param res_len: The maximum length of the descriptor buffer.
    :return: The length of the found descriptor.
    """

    # Get the total length of the configuration descriptors
    config = dev.get_active_configuration()
    conflen = config.wTotalLength

    # Suck in the configuration descriptor list from device

    cbuf = usb.control.get_descriptor(dev, usb.DT_CONFIG_SIZE, usb.DT_CONFIG, 0).tobytes()

    # cbuf = dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
    #                          (usb.util.DESC_TYPE_CONFIG << 8) | 0, 0, conflen)

    if len(cbuf) < conflen:
        logger.warning(
            f"failed to retrieve complete configuration descriptor, got {len(cbuf)}/{conflen}"
        )
        conflen = len(cbuf)

    # Search through the configuration descriptor list
    ret = find_descriptor(cbuf, desc_type, desc_index, resbuf)
    if ret > 1:
        if VERBOSE:
            logger.info("Found descriptor in complete configuration descriptor list")
        return ret

    # Finally try to retrieve it requesting the device directly
    # This is not supported on all devices for non-standard types
    # return dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
    #                          (desc_type << 8) | desc_index, 0, resbuf)
    return usb.control.get_descriptor(dev, usb.DT_CONFIG_SIZE, desc_type, desc_index).tobytes()


def get_cached_extra_descriptor(dev: usb.core.Device,
                                bConfValue: int,
                                intf: int,
                                desc_type: int,
                                desc_index: int,
                                resbuf: bytearray) -> int:
    """
    Get cached extra descriptor from libusb for an interface.

    :param dev: The USB device.
    :param bConfValue: The configuration value.
    :param intf: The interface number.
    :param desc_type: The descriptor type.
    :param desc_index: The descriptor index.
    :param resbuf: The buffer to store the descriptor.
    :param res_len: The maximum length of the descriptor buffer.
    :return: The length of the found descriptor.
    """
    cfg = dev.configurations()[bConfValue - 1]
    try:
        intf_desc = cfg.interfaces()[intf]
    except usb.core.USBError as e:
        if e.errno == usb.core.ENOENT:
            logger.error("Device is unconfigured")
        else:
            logger.error("Failed to get configuration descriptor")
        return -1

    ret = -1

    for altsetting in intf_desc:
        extra = altsetting.extra
        extra_len = altsetting.extra_length

        if extra_len > 1:
            ret = find_descriptor(extra, desc_type, desc_index, resbuf)

        if ret > 1:
            break

    if ret < 2 and VERBOSE:
        logger.info("Did not find cached descriptor")

    return ret


VERSION = (f"{__version__}\n\n"
           f"('Copyright 2005-2008 Weston Schmidt, Harald Welte and OpenMoko Inc.')\n"
           f"{__copyright__}\n"
           f"This program is Free Software and has ABSOLUTELY NO WARRANTY')\n")


class Mode(IntFlag):
    NONE = 0
    VERSION = 1
    LIST = 2
    DETACH = 3
    UPLOAD = 4
    DOWNLOAD = 5


def cpu_to_le16(value):
    return value.to_bytes(2, byteorder='little')


def le16_to_cpu(data):
    return int.from_bytes(data, byteorder='little')


class IntOrBytes:
    def __init__(self, value):
        if isinstance(value, int):
            self._value = value
        elif isinstance(value, bytes):
            self._value = int.from_bytes(value, byteorder='big', signed=True)
        else:
            raise TypeError("Value must be int or bytes")

    def __lt__(self, other):
        if isinstance(other, IntOrBytes):
            return self._value < other._value
        elif isinstance(other, int):
            return self._value < other
        else:
            raise TypeError("Comparison with unsupported type")

    def __eq__(self, other):
        if isinstance(other, IntOrBytes):
            return self._value == other._value
        elif isinstance(other, int):
            return self._value == other
        else:
            raise TypeError("Comparison with unsupported type")

    def __repr__(self):
        return f"IntOrBytes({self._value})"


def main() -> None:
    # Todo: implement

    global VERBOSE

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog="pydfuutil",
        description="Python implementation of DFU-Util tools"
    )

    # Add arguments
    parser.add_argument("-V", "--version", action="version", version=VERSION,
                        help="Print the version number")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print verbose debug statements")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List the currently attached DFU capable USB devices")
    parser.add_argument("-e", "--detach", action="store_true",
                        help="Detach the currently attached DFU capable USB devices")
    parser.add_argument("-d", "--device", metavar="VID:PID",
                        help="Specify Vendor/Product ID of DFU device")
    parser.add_argument("-p", "--path", metavar="BUS-PORT",
                        help="Specify path to DFU device")
    parser.add_argument("-c", "--cfg", metavar="CONFIG_NR",
                        help="Specify the Configuration of DFU device")
    parser.add_argument("-i", "--intf", metavar="INTF_NR",
                        help="Specify the DFU Interface number")
    parser.add_argument("-a", "--alt", metavar="ALT",
                        help="Specify the Altsetting of the DFU Interface")
    parser.add_argument("-t", "--transfer-size", metavar="SIZE",
                        help="Specify the number of bytes per USB Transfer")
    parser.add_argument("-U", "--upload", metavar="FILE",
                        help="Read firmware from device into <file>")
    parser.add_argument("-D", "--download", metavar="FILE",
                        help="Write firmware from <file> into device")
    parser.add_argument("-R", "--reset", action="store_true",
                        help="Issue USB Reset signalling once we're finished")
    parser.add_argument("-s", "--dfuse-address", metavar="ADDRESS",
                        help="ST DfuSe mode, specify target address "
                             "for raw file download or upload. "
                             "Not applicable for DfuSe file (.dfu) downloads")

    # Parse arguments
    args = parser.parse_args()

    dif: dfu.DfuIf = dfu.DfuIf()
    file = DFUFile(None)
    mode = Mode.NONE
    device_id_filter = None
    alt_name = None
    transfer_size = 0
    dfuse_device = 0
    dfuse_options = None
    final_reset = 0

    func_dfu_rt = USB_DFU_FUNC_DESCRIPTOR.parse(bytes(USB_DFU_FUNC_DESCRIPTOR.sizeof()))
    func_dfu = USB_DFU_FUNC_DESCRIPTOR.parse(bytes(USB_DFU_FUNC_DESCRIPTOR.sizeof()))

    if args.verbose:
        VERBOSE = True

    if args.list:
        mode = Mode.LIST

    if args.detach:
        mode = Mode.DETACH

    if args.device:
        device_id_filter = args.device

    if args.path:
        dif.path = args.path
        dif.flags |= dfu.Mode.IFF_PATH
        if ret := resolve_device_path(dif):
            logger.error(f"unable to parse {args.path}")
            sys.exit(2)
        if not ret:
            logger.error(f"cannot find {args.path}")
            sys.exit(1)

    if args.cfg:
        dif.configuration = atoi(args.cfg)
        dif.flags |= dfu.Mode.IFF_CONFIG

    if args.intf:
        dif.interface = atoi(args.intf)
        dif.flags |= dfu.Mode.IFF_IFACE

    if args.alt:
        altsetting = int(args.alt, 0)
        if args.alt.isdigit() and altsetting:
            dif.altsetting = altsetting
        else:
            alt_name = args.alt
        dif.flags |= dfu.Mode.IFF_ALT

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

    print(VERSION)

    if mode == Mode.NONE:
        logger.error("You need to specify one of -D or -U\n\n")
        parser.print_help()
        sys.exit(2)

    if device_id_filter:
        dif.vendor, dif.product = parse_vendprod(device_id_filter)
        logger.info(f"Filter on VID = 0x{dif.vendor:04X} PID = 0x{dif.product:04X}\n")
        if dif.vendor:
            dif.flags |= dfu.Mode.IFF_VENDOR
        if dif.product:
            dif.flags |= dfu.Mode.IFF_PRODUCT

    if VERBOSE:
        logger.setLevel(logging.DEBUG)
        usb_logger.setLevel(logging.DEBUG)

    # libusb init
    libusb_ctx = list(usb.core.find(find_all=True, **dif.device_ids))

    if mode == Mode.LIST:
        list_dfu_interfaces(libusb_ctx)
        sys.exit(0)

    dfu.init(5000)

    dfu_capable = iterate_dfu_devices(libusb_ctx, dif)

    if len(dfu_capable) == 0:
        logger.error("No DFU capable USB device found")
        sys.exit(1)
    elif len(dfu_capable) > 1:
        # We cannot safely support more than one DFU capable device
        # with same vendor/product ID, since during DFU we need to do
        # a USB bus reset, after which the target device will get a
        # new address */
        logger.error("More than one DFU capable USB device found, "
                     "you might try `--list' and then disconnect all but one "
                     "device")
        sys.exit(3)

    # get_first_dfu_device
    if not (dev := dfu_capable[0]):
        sys.exit(3)

    # We have exactly one device. Its libusb_device is now in dif->dev

    logger.info("Opening DFU capable USB device... ")

    _rt_dif: dfu.DfuIf = None

    def get_first_dfu_if(dif_: dfu.DfuIf, v: Any = None):
        nonlocal _rt_dif
        _rt_dif = dif_
        if not _rt_dif:
            logger.error("Cannot open device")
            sys.exit(1)

    find_dfu_if(dev, get_first_dfu_if)
    logger.debug(_rt_dif)

    logger.info(f"ID 0x{_rt_dif.vendor:04X}:0x{_rt_dif.product:04X}")

    quirks = set_quirks(_rt_dif.vendor, _rt_dif.product, _rt_dif.bcdDevice)

    # Obtain run-time DFU functional descriptor without asking device
    # E.g. Free runner does not like to be requested at this point

    ret = get_cached_extra_descriptor(
        _rt_dif.dev, _rt_dif.configuration, _rt_dif.interface,
        # USB_DT_DFU, 0, le16_to_cpu(func_dfu_rt.bcdDFUVersion)
        USB_DT_DFU, 0, USB_DFU_FUNC_DESCRIPTOR.bcdDFUVersion.build(func_dfu_rt.bcdDFUVersion)
    )
    ret = IntOrBytes(ret)
    if ret == 7:
        logger.info("Deducing device DFU version from functional descriptor "
                    "length")
        func_dfu_rt.bcdDFUVersion = 0x0100
    elif ret < 9:
        logger.warning("Can not find cached DFU functional "
                       "descriptor")
        logger.warning("Assuming DFU version 1.0")
        func_dfu_rt.bcdDFUVersion = 0x0100

    logger.info(f"Run-time device DFU version 0x{func_dfu_rt.bcdDFUVersion:04X}")

    # Transition from run-Time mode to DFU mode

    # status_again
    def check_status():
        logger.debug('Status again')
        _log_msg = "Determining device status: "
        _, status = dfu.get_status(_rt_dif.dev, _rt_dif.interface)
        if _ < 0:
            logger.error(f"{_log_msg}error get_status")
            sys.exit(1)
        logger.info(f"{_log_msg}state = {dfu.state_to_string(status.bState)}, "
                    f"status = {status.bStatus}")

        if not quirks & QUIRK_POLLTIMEOUT:
            milli_sleep(status.bwPollTimeout)
        return status

    while not (_rt_dif.flags & dfu.Mode.IFF_DFU):
        # In the 'first round' during runtime mode, there can only be one
        # DFU Interface descriptor according to the DFU Spec.

        # FIXME: check if the selected device really has only one

        logger.info("Claiming USB DFU Runtime Interface...")
        try:
            usb.util.claim_interface(_rt_dif.dev, _rt_dif.interface)
        except usb.core.USBError as exc:
            logger.error(f"Cannot claim interface {_rt_dif.interface}")
            sys.exit(1)

        try:
            _rt_dif.dev.set_interface_altsetting(_rt_dif.interface, 0)
        except usb.core.USBError as exc:
            logger.error(f"Cannot set alt interface zero")
            sys.exit(1)

        status = check_status()

        if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
            logger.info("Device really in Runtime Mode, send DFU "
                        "detach request...")

            if IntOrBytes(dfu.detach(_rt_dif.dev, _rt_dif.interface, 1000)) < 0:
                logger.error("error detaching")
                sys.exit(1)

            if func_dfu_rt.bmAttributes & bmAttributes.USB_DFU_WILL_DETACH:
                logger.info("Device will detach and reattach...")
            else:
                logger.info("Resetting USB...\n")
                try:
                    _rt_dif.dev.reset()
                except usb.core.USBError as exc:
                    logger.error("error resetting after detach")
            milli_sleep(2000)
            break
        elif status.bState == dfu.State.DFU_ERROR:
            logger.error("dfuERROR, clearing status")
            if dfu.clear_status(_rt_dif.dev, _rt_dif.interface) < 0:
                logger.error("error detaching")
                sys.exit(1)
        else:
            logger.info("Runtime device already in DFU state ?!?")
            break

        usb.util.release_interface(_rt_dif.dev, _rt_dif.interface)
        usb.util.dispose_resources(_rt_dif.dev)

        if mode == Mode.DETACH:
            usb.util.release_interface(_rt_dif.dev, _rt_dif.interface)
            usb.util.dispose_resources(_rt_dif.dev)
            sys.exit(0)

        if dif.flags & dfu.Mode.IFF_PATH:
            ret = resolve_device_path(dif)
            if IntOrBytes(ret) < 0:
                logger.error(f"internal error: cannot re-parse {dif.path}")
                sys.exit(1)
            if not ret:
                logger.error("Cannot resolve path after RESET?")
                sys.exit(1)

        dfu_capable = iterate_dfu_devices(libusb_ctx, dif)
        if len(dfu_capable) == 0:
            logger.error("Lost device after RESET?")
            sys.exit(1)
        elif len(dfu_capable) > 1:
            logger.error("More than one DFU capable USB "
                         "device found, you might try `--list' and "
                         "then disconnect all but one device")
            sys.exit(1)

    def get_first_detached_dfu_if(dif_: dfu.DfuIf, v: Any = None):
        nonlocal dif
        dif = dif_
        if not dif:
            logger.error("Cannot open device")
            sys.exit(1)

    find_dfu_if(dev, get_first_detached_dfu_if)
    logger.debug(dif)

    logger.info("Opening DFU USB Device...")

    # we're already in DFU mode, so we can skip the detach/reset
    # procedure

    # dfustate
    logger.debug('Dfu state...')

    if alt_name:
        if not (n := find_dfu_if(dif.dev, alt_by_name, alt_name)):
            logger.error(f"No such Alternate Setting: {alt_name}")
            sys.exit(1)
        if n < 0:
            logger.error(f"Error {n} in name lookup")
            sys.exit(1)
        dif.altsetting = n - 1

    if (num_ifs := count_matching_dfu_if(dif)) < 0:
        logger.error("No matching DFU Interface after RESET?!?")
        sys.exit(1)
    elif num_ifs > 1:
        logger.warning("Detected interfaces after DFU transition")
        list_dfu_interfaces(libusb_ctx)
        logger.error(f"We have {num_ifs} DFU Interfaces/Altsettings,"
                     " you have to specify one via --intf / --alt"
                     " options")
        sys.exit(1)

    if not get_matching_dfu_if(dif):
        logger.error("Can't find the matching DFU interface/altsetting")
        sys.exit(1)

    print_dfu_if(dif, None)
    if (active_alt_name := get_alt_name(dif)) and len(active_alt_name) > 0:
        dif.alt_name = active_alt_name
    else:
        dif.alt_name = None

    # # Note: uncomment on need
    # logger.info(f"Setting Configuration {dif.configuration}...")
    # try:
    #     dif.dev.set_configuration(dif.configuration)
    # except usb.core.USBError as e:
    #     logger.error("Cannot set configuration")
    #     sys.exit(1)

    logger.info("Claiming USB DFU Interface...")
    try:
        usb.util.claim_interface(dif.dev, dif.interface)
    except usb.core.USBError as e:
        logger.error("Cannot claim interface")
        sys.exit(1)

    logger.info(f"Setting Alternate Setting {dif.altsetting} ...\n")
    try:
        dif.dev.set_interface_altsetting(dif.interface, dif.altsetting)
    except usb.core.USBError as e:
        logger.error("Cannot set alternate interface")
        sys.exit(1)

    status = check_status()
    while status.bState != dfu.State.DFU_IDLE:

        if status.bState in (dfu.State.APP_IDLE, dfu.State.APP_DETACH):
            logger.error("Device still in Runtime Mode!")
            sys.exit(1)

        elif status.bState == dfu.State.DFU_ERROR:
            logger.error("dfuERROR, clearing status")
            if dfu.clear_status(dif.dev, dif.interface) < 0:
                logger.error("error clear_status")
                sys.exit(1)

            status = check_status()

        elif status.bState == (dfu.State.DFU_DOWNLOAD_IDLE, dfu.State.DFU_UPLOAD_IDLE):
            logger.warning("aborting previous incomplete transfer")
            if dfu.abort(dif.dev, dif.interface) < 0:
                logger.error("can't send DFU_ABORT")
                sys.exit(1)

            status = check_status()

        elif status.bState == dfu.State.DFU_IDLE:
            logger.info("dfuIDLE, continuing")
            break

    if status.bStatus != dfu.Status.OK:
        logger.warning(f"DFU Status: {dfu.status_to_string(status.bStatus)}")
        # Clear our status & try again.
        dfu.clear_status(dif.dev, dif.interface)
        _, status = dfu.get_status(dif.dev, dif.interface)
        if status.bStatus != dfu.Status.OK:
            logger.error(f"{status.bStatus}")
            sys.exit(1)
        if not quirks & QUIRK_POLLTIMEOUT:
            milli_sleep(status.bwPollTimeout)

    logger.debug(f"State: {dfu.state_to_string(status.bState)}, "
                 f"Status: {dfu.status_to_string(status.bStatus)} Continue...")

    # Get the DFU mode DFU functional descriptor
    # If it is not found cached, we will request it from the device

    ret = get_cached_extra_descriptor(
        dif.dev, dif.configuration, dif.interface,
        USB_DT_DFU, 0, USB_DFU_FUNC_DESCRIPTOR.bcdDFUVersion.build(func_dfu.bcdDFUVersion)
    )
    ret = IntOrBytes(ret)

    if ret < 7:
        logger.error("obtaining cached DFU functional descriptor")
        ret = usb_get_any_descriptor(
            dif.dev, USB_DT_DFU, 0,
            USB_DFU_FUNC_DESCRIPTOR.bcdDFUVersion.build(func_dfu_rt.bcdDFUVersion))
        ret = IntOrBytes(ret)

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

    if quirks & QUIRK_FORCE_DFU11:
        func_dfu.bcdDFUVersion = 0x0110

    logger.info(f"DFU mode device DFU version  0x{func_dfu.bcdDFUVersion:04X}")

    if func_dfu.bcdDFUVersion == 0x11a:
        dfuse_device = 1

    # If not overridden by the user
    if transfer_size:
        logger.info(f"Device returned transfer size {transfer_size}")
    else:
        logger.error("Transfer size must be specified")
        sys.exit(1)

    # autotools lie when cross-compiling for Windows using mingw32/64
    if HAVE_GETPAGESIZE:
        # limitation of Linux usbdevio
        page_size = os.sysconf(os.sysconf_names['SC_PAGE_SIZE'])
        if transfer_size > page_size:
            transfer_size = page_size
            logger.info(f"Limited transfer size to {transfer_size}")

    # DFU specification
    # if dif.dev:  # strange think, unreachable
    #     logger.error(f"Failed to get device descriptor")
    #     sys.exit(1)

    if transfer_size < dif.dev.bMaxPacketSize0:
        logger.info(f"Adjusted transfer size to {transfer_size}")

    if mode == Mode.UPLOAD:
        # open for "exclusive" writing in a portable way
        try:
            with open(file.name, "ab") as file.filep:
                if os.path.getsize(file.name) != 0:
                    logger.info(f"{file.name}: File exists")
                    sys.exit(1)

                if dfuse_device or dfuse_options:
                    if dfuse.do_upload(dif, transfer_size, file, dfuse_options) < 0:
                        sys.exit(1)
                else:
                    if dfu_load.do_upload(dif, transfer_size, file) < 0:
                        sys.exit(1)

        except OSError as e:
            logger.error(e)
            sys.exit(1)

    elif mode == Mode.DOWNLOAD:
        try:
            # Open file for reading in binary mode
            with open(file.name, "rb") as filep:
                if not filep:
                    logger.error(f"Error: Failed to open {file.name}")
                    sys.exit(1)

                # Parse DFU suffix
                ret = parse_dfu_suffix(file)
                if ret < 0:
                    sys.exit(1)
                elif ret == 0:
                    logger.warning("File has no DFU suffix")
                elif file.bcdDFU != 0x0100 and file.bcdDFU != 0x011a:
                    logger.error(f"Unsupported DFU file revision 0x{file.bcdDFU:04x}")
                    sys.exit(1)

                # Check vendor ID
                if file.idVendor != 0xffff and dif.vendor != file.idVendor:
                    logger.warning(f"Warning: File vendor ID 0x{file.idVendor:04x} "
                                   f"does not match device 0x{dif.vendor:04x}")

                # Check product ID
                if file.idProduct != 0xffff and dif.product != file.idProduct:
                    logger.warning(f"File product ID 0x{file.idProduct:04x} "
                                   f"does not match device 0x{dif.product:04x}")

                # Perform download based on conditions
                if dfuse_device or dfuse_options or file.bcdDFU == 0x011a:
                    if dfuse.do_dnload(dif, transfer_size, file, dfuse_options) < 0:
                        sys.exit(1)
                else:
                    if dfu_load.do_dnload(dif, transfer_size, file, quirks, VERBOSE) < 0:
                        sys.exit(1)

        except OSError as e:
            logger.error(e)
            sys.exit(1)

    else:
        logger.error(f"Unsupported mode: {mode}")
        sys.exit(1)

    if final_reset:
        if IntOrBytes(dfu.detach(dif.dev, dif.interface, 1000)) < 0:
            logger.error("can't detach")
        logger.info("Resetting USB to switch back to runtime mode")
        try:
            dif.dev.reset()
        except usb.core.USBError as e:
            logger.error("error resetting after download")

    usb.util.release_interface(dif.dev, dif.interface)
    usb.util.dispose_resources(dif.dev)
    exit(0)


if __name__ == '__main__':
    main()

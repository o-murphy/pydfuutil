"""
pydfuutil
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
Based on existing code of dfu-programmer-0.4
"""
import errno
import re
from typing import Any, Callable

import usb.core

from pydfuutil import __version__, __copyright__, dfu

MAX_DESC_STR_LEN = 253


# TODO: not implemented yet


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
                handler: Callable[[dfu.DfuIf, Any], int],
                v: Any) -> int:
    """
    Find DFU interface for a given USB device.

    :param dev: The USB device.
    :param handler: Callback function to handle the found DFU interface.
    :param v: Additional user-defined data for the callback function.
    :return: 0 if no DFU interface is found, or the result of the handler function.
    """
    desc = dev.get_active_configuration().desc

    for cfg in desc:
        for intf in cfg:
            if intf.bInterfaceClass == 0xfe and intf.bInterfaceSubClass == 1:
                dfu_if = dfu.DfuIf(
                    vendor=desc.idVendor,
                    product=desc.idProduct,
                    bcdDevice=desc.bcdDevice,
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
    intf = cfg[(dfu_if.interface, dfu_if.altsetting)]

    alt_name_str_idx = intf.iInterface

    if alt_name_str_idx:
        if not dfu_if.dev.handle:
            try:
                dfu_if.dev.handle = usb.util.find_descriptor(dev, find_all=True)
            except usb.core.USBError:
                dfu_if.dev.handle = None

        if dfu_if.dev.handle:
            try:
                return dfu_if.dev.handle.get_string(alt_name_str_idx, MAX_DESC_STR_LEN)
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
    name = get_alt_name(dfu_if)
    if name is None:
        name = b"UNDEFINED"

    print(f"Found {'DFU' if dfu_if.flags & dfu.Mode.IFF_DFU else 'Runtime'}: "
          f"[{dfu_if.vendor:04x}:{dfu_if.product:04x}] devnum={dfu_if.devnum}, "
          f"cfg={dfu_if.configuration}, intf={dfu_if.interface}, "
          f"alt={dfu_if.altsetting}, name=\"{name.decode('utf-8')}\"")

    return 0


def list_dfu_interfaces(ctx: 'usb.core.Context') -> int:
    """
    Walk the device tree and print out DFU devices.

    :param ctx: The USB context.
    :return: 0 on success.
    """
    list = ctx.get_device_list()

    for dev in list:
        find_dfu_if(dev, print_dfu_if, None)

    usb.util.dispose_resources(ctx)
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


def _count_cb(dif: dfu.DfuIf, v: list) -> int:
    """
    Callback function to count DFU interfaces.

    :param dif: The DFU interface struct.
    :param v: Pointer to the count variable.
    :return: Always returns 0.
    """
    count: list[int] = v
    count[0] += 1
    return 0


def count_dfu_interfaces(dev: usb.core.Device) -> int:
    """
    Count DFU interfaces within a single device.

    :param dev: The USB device.
    :return: The number of DFU interfaces found.
    """
    num_found: int = 0
    find_dfu_if(dev, _count_cb, num_found)
    return num_found


def iterate_dfu_devices(ctx: 'usb.core.Context', dif: dfu.DfuIf, action, user) -> int:
    """
    Iterate over all matching DFU capable devices within the system.

    :param ctx: The USB context.
    :param dif: The DFU interface.
    :param action: The action to perform for each device.
    :param user: Additional user-defined data.
    :return: 0 on success, or an error code.
    """
    list = ctx.get_device_list()
    for dev in list:
        desc = dev.get_device_descriptor()

        if dif and (dif.flags & dfu.Mode.IFF_DEVNUM) and (dev.bus != dif.bus or dev.address != dif.devnum):
            continue
        if dif and (dif.flags & dfu.Mode.IFF_VENDOR) and desc.idVendor != dif.vendor:
            continue
        if dif and (dif.flags & dfu.Mode.IFF_PRODUCT) and desc.idProduct != dif.product:
            continue
        if not count_dfu_interfaces(dev):
            continue

        retval = action(dev, user)
        if retval:
            return retval

    return 0


def found_dfu_device(dev: usb.core.Device, dif: dfu.DfuIf) -> int:
    """
    Save the DFU-capable device in dif.dev.

    :param dev: The USB device.
    :param dif: The DFU interface instance.
    :return: 1 always.
    """
    dif.dev = dev
    return 1


def get_first_dfu_device(ctx: 'usb.core.Context', dif: dfu.DfuIf) -> int:
    """
    Find the first DFU-capable device and save it in dif.dev.

    :param ctx: The USB context.
    :param dif: The DFU interface struct.
    :return: 0 on success, or an error code.
    """
    return iterate_dfu_devices(ctx, dif, found_dfu_device, dif)


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


def count_dfu_devices(ctx: 'usb.core.Context', dif: dfu.DfuIf) -> int:
    """
    Count the number of DFU devices connected to the USB context.

    :param ctx: The libusb context.
    :param dif: The DFU interface struct.
    :return: The number of DFU devices found.
    """
    num_found = 0

    iterate_dfu_devices(ctx, dif, count_one_dfu_device, num_found)
    return num_found


def parse_vendprod(string: str) -> tuple[int, int]:
    """
    Parse a string containing vendor and product IDs in hexadecimal format.

    :param string: The string containing vendor and product IDs separated by ':'.
    :return: A tuple containing the vendor and product IDs.
    """
    vendor = 0
    product = 0

    vendor_str, _, product_str = string.partition(':')

    if vendor_str:
        vendor = int(vendor_str, 16)
    if product_str:
        product = int(product_str, 16)

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
        print("USB device paths are not supported by this dfu-util.\n")
        sys.exit(1)


def find_descriptor(desc_list: list, desc_type: int, desc_index: int,
                    res_buf: bytearray, res_size: int) -> int:
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
            print("Error: Invalid descriptor list")
            return -1

        if desc_list[p + 1] == desc_type and hit == desc_index:
            if desclen > res_size:
                desclen = res_size
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
                           resbuf: bytearray,
                           res_len: int) -> int:
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
    conflen = config.desc.wTotalLength

    # Suck in the configuration descriptor list from device
    cbuf = dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
                                    (usb.util.DESC_TYPE_CONFIG << 8) | 0, 0, conflen)

    if len(cbuf) < conflen:
        print("Warning: failed to retrieve complete configuration descriptor, got {}/{}".format(len(cbuf), conflen))
        conflen = len(cbuf)

    # Search through the configuration descriptor list
    ret = find_descriptor(cbuf, desc_type, desc_index, resbuf, res_len)
    if ret > 1:
        if verbose:
            print("Found descriptor in complete configuration descriptor list")
        return ret

    # Finally try to retrieve it requesting the device directly
    # This is not supported on all devices for non-standard types
    return dev.ctrl_transfer(usb.util.ENDPOINT_IN, usb.util.GET_DESCRIPTOR,
                                    (desc_type << 8) | desc_index, 0, resbuf, res_len)


def get_cached_extra_descriptor(dev: usb.core.Device,
                                bConfValue: int,
                                intf: int,
                                desc_type: int,
                                desc_index: int,
                                resbuf: bytearray,
                                res_len: int) -> int:
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
    cfg = dev.get_active_configuration()

    try:
        intf_desc = cfg[(bConfValue, intf)]
    except usb.core.USBError as e:
        if e.errno == usb.core.ENOENT:
            print("Error: Device is unconfigured")
        else:
            print("Error: Failed to get configuration descriptor")
        return -1

    ret = -1

    for altsetting in intf_desc:
        extra = altsetting.extra
        extra_len = altsetting.extra_length

        if extra_len > 1:
            ret = find_descriptor(extra, desc_type, desc_index, resbuf, res_len)

        if ret > 1:
            break

    if ret < 2 and verbose:
        print("Did not find cached descriptor")

    return ret


def help_() -> None:
    print(
        "  -h --help\t\t\tPrint this help message\n"
        "  -V --version\t\t\tPrint the version number\n"
        "  -v --verbose\t\t\tPrint verbose debug statements\n"
        "  -l --list\t\t\tList the currently attached DFU capable USB devices\n"
    )
    print(
        "  -e --detach\t\t\tDetach the currently attached DFU capable USB devices\n"
        "  -d --device vendor:product\tSpecify Vendor/Product ID of DFU device\n"
        "  -p --path bus-port. ... .port\tSpecify path to DFU device\n"
        "  -c --cfg config_nr\t\tSpecify the Configuration of DFU device\n"
        "  -i --intf intf_nr\t\tSpecify the DFU Interface number\n"
        "  -a --alt alt\t\t\tSpecify the Altsetting of the DFU Interface\n"
        "\t\t\t\tby name or by number\n"
    )
    print(
        "  -t --transfer-size\t\tSpecify the number of bytes per USB Transfer\n"
        "  -U --upload file\t\tRead firmware from device into <file>\n"
        "  -D --download file\t\tWrite firmware from <file> into device\n"
        "  -R --reset\t\t\tIssue USB Reset signalling once we're finished\n"
        "  -s --dfuse-address address\tST DfuSe mode, specify target address for\n"
        "\t\t\t\traw file download or upload. Not applicable for\n"
        "\t\t\t\tDfuSe file (.dfu) downloads\n"
    )


def print_version() -> None:
    print(f"{__version__}\n\n")
    print('Copyright 2005-2008 Weston Schmidt, Harald Welte and OpenMoko Inc.\n'
          f'{__copyright__}\n'
          'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


def main(argv):
    # Todo: implement
    raise NotImplementedError


if __name__ == '__main__':
    import sys

    main(sys.argv)

"""
Functions for detecting DFU USB entities
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
import struct
import sys
from dataclasses import dataclass
from typing import Generator

import usb.core

from pydfuutil.dfu import DfuIf, Mode
from pydfuutil.logger import logger
from pydfuutil.quirks import get_quirks
from pydfuutil.usb_dfu import USB_DT_DFU, USB_DT_DFU_SIZE, FuncDescriptor, BmAttributes

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

MAX_DESC_STR_LEN = 253
MAX_PATH_LEN = 20


@dataclass
class DfuUtil:
    dfu_if: DfuIf = None
    match_path: str = None
    match_vendor: int = -1
    match_product: int = -1
    match_vendor_dfu: int = -1
    match_product_dfu: int = -1
    match_config_index: int = -1
    match_iface_index: int = -1
    match_iface_alt_index: int = -1
    match_devnum: int = -1
    match_iface_alt_name: str = None
    match_serial: str = None
    match_serial_dfu: str = None

    dfu_root: DfuIf = None

    path_buf: str = None


def cpu_to_le16(value: int) -> bytes:
    """Convert int to uint16le"""
    return value.to_bytes(2, byteorder='little')


def le16_to_cpu(data: bytes) -> int:
    """Convert uint16le to int"""
    return int.from_bytes(data, byteorder='little')


def find_descriptor(desc_list: list[int], desc_type: int, res_buf: bytearray):
    """
    Look for a descriptor in a concatenated descriptor list. Will
    return upon the first match of the given descriptor type. Returns length of
    found descriptor, limited to res_size
    :return: 
    """
    p = 0
    res_size = len(res_buf)
    list_len = len(desc_list)

    if list_len < 2:
        return -1

    while p + 1 < list_len:
        desclen = desc_list[p]
        if desclen == 0:
            print("Invalid descriptor list")
            return -1
        if desc_list[p + 1] == desc_type:
            if desclen > res_size:
                desclen = res_size
            if p + desclen > list_len:
                desclen = list_len - p
            res_buf[:] = desc_list[p:p + desclen]
            return 0
        p += desc_list[p]

    return -1


def get_utf8_string_descriptor():
    raise NotImplementedError


def get_string_descriptor_ascii():
    raise NotImplementedError


def probe_configuration(dev: usb.core.Device, intf: usb.core.Interface):
    raise NotImplementedError


def get_path(dev) -> str:
    path = None
    try:
        # Get the bus and device address
        bus_num = dev.bus
        device_num = dev.address

        # Construct the path
        path = f"{bus_num}-{device_num}"

        # If the device supports port numbers, get them
        if hasattr(dev, 'port_numbers'):
            port_nums = dev.port_numbers
            if port_nums is not None:
                path += '.' + '.'.join(map(str, port_nums))

    except Exception as e:
        # Handle any exceptions, like if the device does not support port numbers
        logger.error(f"Error while getting path: {e}")

    DfuUtil.path_buf = path
    return path


def probe_devices(ctx: Generator[usb.core.Device, None, None]) -> None:
    for dev in ctx:
        intf = dev.get_active_configuration().desc
        path = get_path(dev)

        if DfuUtil.match_path is not None and path != DfuUtil.match_path:
            continue

        probe_configuration(dev, intf)

        # Claim the interface to perform operations
        usb.util.claim_interface(dev, intf)

        # Dispose resources after probing
        usb.util.dispose_resources(dev)


def disconnect_devices() -> None:
    pdfu = DfuUtil.dfu_root

    while pdfu is not None:
        next_dfu = pdfu.next

        usb.util.dispose_resources(pdfu.dev)
        pdfu.dev = None
        pdfu.alt_name = None
        pdfu.serial_name = None

        pdfu = next_dfu

    DfuUtil.dfu_root = None


def print_dfu_if(dfu_if: DfuIf) -> None:
    print(f"Found {'DFU' if dfu_if.flags & Mode.IFF_DFU else 'Runtime'}: "
          f'[{dfu_if.vendor:04x}:{dfu_if.product:04x}] '
          f'ver={dfu_if.bcdDevice:04x}, devnum={dfu_if.devnum}, '
          f'cfg={dfu_if.configuration}, intf={dfu_if.interface}, '
          f'path="{get_path(dfu_if.dev)}", '
          f'alt={dfu_if.altsetting}, name="{dfu_if.alt_name}", '
          f'serial="{dfu_if.serial_name}"')


# Walk the device tree and print out DFU devices
def list_dfu_interfaces() -> None:
    pdfu = DfuUtil.dfu_root
    while pdfu is not None:
        print_dfu_if(pdfu)
        pdfu = pdfu.next


__all__ = (
    'Mode',
    'MAX_DESC_STR_LEN',
    'probe_devices',
    'disconnect_devices',
    'print_dfu_if',
    'list_dfu_interfaces',
)




def probe_dfu_func_descriptor():
    func_dfu = FuncDescriptor()

    def find_func_desc(dev: usb.core.Device,
                       func_dfu: FuncDescriptor) -> int:
        try:
            ret_val = usb.control.get_descriptor(
                dev, usb.DT_CONFIG_SIZE, usb.DT_CONFIG, 0
            )
            data = ret_val.tobytes()
            (func_dfu.bLength,
             func_dfu.bDescriptorType,
             bmAttributes,
             func_dfu.wDetachTimeOut,
             func_dfu.wTransferSize,
             func_dfu.bcdDFUVersion) = struct.unpack(
                '<BBBHHH', data)

            func_dfu.bmAttributes = BmAttributes(bmAttributes)
            return 0
        except usb.control.USBError:
            return -1


    def found_dfu() -> None:
        print('found dfu')
        if func_dfu.bLength == 7:
            _logger.info("Deducing device DFU version from functional descriptor length")
        elif func_dfu.bLength < 9:
            _logger.error("Error obtaining DFU functional descriptor")
            _logger.error("Please report this as a bug!")
            _logger.warning("Assuming DFU version 1.0")
            func_dfu.bcdDFUVersion = 0x0100
            _logger.warning("Transfer size can not be detected")
            func_dfu.wTransferSize = 0

        intf: usb.core.Interface
        for intf in dev.get_active_configuration():

            if (DfuUtil.match_iface_index > -1
                    and DfuUtil.match_iface_index != intf.index):
                continue

            if not intf:
                break

            num_altsettings = 0
            for alt in intf:
                num_altsettings += 1

            multiple_alt = num_altsettings > 0

        # for alt_idx in range(intf.bNumEndpoints):
        #     quirks = get_quirks(dev.idVendor, dev.idProduct, dev.bcdDevice)
        #
        #     intf = uif.endpoints()
        #     print('ends', intf)

    dev: usb.core.Device = usb.core.find(find_all=False, idVendor=0x1fc9)
    cfgs = dev.configurations()
    for cfg in cfgs:

        # NOTE: no need to find on cfg
        ret = find_func_desc(dev, func_dfu)
        if ret > -1:
            # goto found_dfu
            return found_dfu()

        uif: usb.core.Interface
        for uif in cfg:
            if not uif:
                break

            if uif.bInterfaceClass != 0xfe or uif.bInterfaceSubClass != 1:
                continue

            # NOTE: no need to find on intf
            ret = find_func_desc(dev, func_dfu)
            if ret > -1:
                # goto found_dfu
                return found_dfu()

            DfuUtil.has_dfu = 1

        if DfuUtil.has_dfu == 1:
            # Finally try to retrieve it requesting the
            # device directly This is not supported on
            # all devices for non-standard types

            # NOTE: no need to find on intf
            ret = find_func_desc(dev, func_dfu)
            if ret > -1:
                # goto found_dfu
                return found_dfu()

            _logger.warning("Device has DFU interface, "
                            "but has no DFU functional descriptor")

            # fake version 1.0
            func_dfu.bLength = 7
            func_dfu.bcdDFUVersion = 0x0100

            # goto found_dfu
            return found_dfu()


if __name__ == '__main__':
    probe_dfu_func_descriptor()

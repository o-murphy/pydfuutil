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
from dataclasses import dataclass
from typing import Generator

import usb.core

from pydfuutil import dfu
from pydfuutil.dfu import DfuIf, IFF
from pydfuutil.logger import logger
from pydfuutil.quirks import get_quirks, QUIRK
from pydfuutil.usb_dfu import FuncDescriptor, USB_DT_DFU, USB_DT_DFU_SIZE

_logger = logger.getChild('dfu_util')

MAX_DESC_STR_LEN = 253
MAX_PATH_LEN = 20


class DfuUtilMeta(type):
    def __repr__(cls):
        _fields = ', '.join(f'{field}={getattr(cls, field)!r}'
                            for field in getattr(cls, '__dataclass_fields__'))
        return f"DfuUtil({_fields})"


@dataclass
class DfuUtil(metaclass=DfuUtilMeta):
    dfu_if: DfuIf = None
    match_path: str = None
    match_vendor: int = -1
    match_product: int = -1
    match_vendor_dfu: int = -1
    match_product_dfu: int = -1
    match_config_index: int = -1
    match_iface_index: int = -1
    match_iface_alt_index: int = -1
    match_dev_num: int = -1
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


def find_descriptor(desc_list: list[int], desc_type: int, res_buf: bytearray) -> [bytearray, None]:
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
        return None

    while p + 1 < list_len:
        desc_len = desc_list[p]
        if desc_len == 0:
            _logger.warning("Invalid descriptor list")
            return None
        if desc_list[p + 1] == desc_type:
            if desc_len > res_size:
                desc_len = res_size
            if p + desc_len > list_len:
                desc_len = list_len - p
            res_buf[:] = desc_list[p:p + desc_len]
            return res_buf
        p += desc_list[p]

    return None


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

    DfuUtil.path_buf = path[MAX_PATH_LEN:]
    return path


def probe_devices(ctx: Generator[usb.core.Device, None, None]) -> None:
    for dev in ctx:
        path = get_path(dev)
        if DfuUtil.match_path is not None and path != DfuUtil.match_path:
            continue
        probe_configuration(dev)
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
    print(f"Found {'DFU' if dfu_if.flags & IFF.DFU else 'Runtime'}: "
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


def get_altsettings(
        config: usb.core.Configuration,
        interface: int) -> Generator[usb.core.Interface, None, None]:
    # Get the alternate settings of the interface
    return usb.util.find_descriptor(config, find_all=True, bInterfaceNumber=interface)


def _found_dfu(dev: usb.core.Device, cfg: usb.core.Configuration, func_dfu: FuncDescriptor) -> None:
    if func_dfu.bLength == 7:
        _logger.info("Deducing device DFU version from functional descriptor length")
    elif func_dfu.bLength < 9:
        _logger.error("Error obtaining DFU functional descriptor")
        _logger.error("Please report this as a bug!")
        _logger.warning("Assuming DFU version 1.0")
        func_dfu.bcdDFUVersion = 0x0100
        _logger.warning("Transfer size can not be detected")
        func_dfu.wTransferSize = 0

    uif: usb.core.Interface
    for uif in dev.get_active_configuration():

        if (DfuUtil.match_iface_index > -1
                and DfuUtil.match_iface_index != uif.index):
            continue

        if not uif:
            break

        altsetting = list(get_altsettings(cfg, uif.bInterfaceNumber))

        multiple_alt = len(altsetting) > 0

        for alt in altsetting:

            quirks = get_quirks(dev.idVendor, dev.idProduct, dev.bcdDevice)

            intf = alt

            # DFU subclass
            if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
                continue

            dfu_mode = (intf.bInterfaceProtocol == 2)

            # ST DfuSe devices often use bInterfaceProtocol 0 instead of 2
            if func_dfu.bcdDFUVersion == 0x011a and intf.bInterfaceProtocol == 0:
                dfu_mode = True

            # LPC DFU bootloader has bInterfaceProtocol 1 (Runtime) instead of 2
            if (dev.idVendor == 0x1fc9 and dev.idProduct == 0x000c
                    and intf.bInterfaceProtocol == 1):
                dfu_mode = True

            # Old Jabra devices may have bInterfaceProtocol 0 instead of 2.
            # Also, runtime PID and DFU pid are the same.
            # In DFU mode, the configuration descriptor has only 1 interface.
            if (dev.idVendor == 0x0b0e
                    and dev.bInterfaceProtocol == 0
                    and cfg.bNumInterfaces == 1):
                dfu_mode = True

            if (dfu_mode
                    and DfuUtil.match_iface_index > -1
                    and DfuUtil.match_iface_alt_index != intf.bAlternateSetting):
                continue

            if dfu_mode:
                if ((DfuUtil.match_vendor_dfu >= 0
                     and DfuUtil.match_vendor_dfu != dev.idVendor) or
                        (DfuUtil.match_product_dfu >= 0
                         and DfuUtil.match_product_dfu != dev.idProduct)):
                    continue

            else:
                if ((DfuUtil.match_vendor >= 0
                     and DfuUtil.match_vendor != dev.idVendor) or
                        (DfuUtil.match_product >= 0
                         and DfuUtil.match_product != dev.idVendor)):
                    continue

            if DfuUtil.match_dev_num >= 0 and DfuUtil.match_dev_num != dev.address:
                continue

            if intf.iInterface != 0:
                alt_name = usb.util.get_string(dev, intf.iInterface)
            else:
                alt_name = None

            if not alt_name:
                alt_name = "UNKNOWN"

            if dev.iSerialNumber != 0:
                if quirks and QUIRK.UTF8_SERIAL:
                    serial_name = usb.util.get_string(dev, dev.iSerialNumber)
                    if serial_name:
                        serial_name += '0'
                else:
                    serial_name = usb.util.get_string(dev, dev.iSerialNumber)
            else:
                serial_name = None
            if not serial_name:
                serial_name = "UNKNOWN"

            if (dfu_mode
                    and DfuUtil.match_iface_alt_name is not None
                    and alt_name != DfuUtil.match_iface_alt_name):
                continue

            if dfu_mode:
                if (DfuUtil.match_serial_dfu is not None
                        and DfuUtil.match_serial_dfu != serial_name):
                    continue
            elif (DfuUtil.match_serial is not None
                  and DfuUtil.match_serial != serial_name):
                continue

            pdfu = DfuIf(
                dev=dev,
                vendor=dev.idVendor,
                product=dev.idProduct,
                bcdDevice=dev.bcdDevice,
                configuration=cfg.bConfigurationValue,
                interface=intf.bInterfaceNumber,
                altsetting=intf.bAlternateSetting,
                alt_name=alt_name,
                bus=dev.bus,
                devnum=dev.address,
                bMaxPacketSize0=dev.bMaxPacketSize0,
                quirks=quirks,
                serial_name=serial_name,
                func_dfu=func_dfu,
            )

            pdfu.flags |= dfu.IFF.DFU if dfu_mode else 0
            pdfu.flags |= dfu.IFF.ALT if multiple_alt else 0
            pdfu.func_dfu.bcdDFUVersion = (0x0110 if pdfu.quirks & QUIRK.FORCE_DFU11
                                           else pdfu.func_dfu.bcdDFUVersion)

            # append to list
            if DfuUtil.dfu_root is None:
                DfuUtil.dfu_root = pdfu
            else:
                last = DfuUtil.dfu_root
                while last.next is not None:
                    last = last.next
                last.next = pdfu
    usb.util.dispose_resources(dev)


def probe_configuration(dev: usb.core.Device) -> None:
    cfgs = dev.configurations()
    for cfg in cfgs:

        if cfg is None:
            return

        if ret := find_descriptor(cfg.extra_descriptors, USB_DT_DFU,
                                  bytearray(USB_DT_DFU_SIZE)):
            func_dfu = FuncDescriptor.from_bytes(ret)
            _found_dfu(dev, cfg, func_dfu)
            return

        has_dfu = False
        uif: usb.core.Interface
        for uif in cfg:
            if not uif:
                break

            for alt in get_altsettings(cfg, uif.bInterfaceNumber):
                intf = alt

                if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
                    continue

                if ret := find_descriptor(intf.extra_descriptors,
                                          USB_DT_DFU,
                                          bytearray(USB_DT_DFU_SIZE)):
                    func_dfu = FuncDescriptor.from_bytes(ret)
                    # goto found_dfu
                    _found_dfu(dev, cfg, func_dfu)
                    return

                has_dfu = True

        if has_dfu:
            # Finally try to retrieve it requesting the
            # device directly This is not supported on
            # all devices for non-standard types

            # NOTE: no need to find on intf
            try:
                if ret := usb.control.get_descriptor(
                        dev, usb.DT_CONFIG_SIZE, usb.DT_CONFIG, 0
                ):
                    func_dfu = FuncDescriptor.from_bytes(ret.tobytes())
                    _found_dfu(dev, cfg, func_dfu)
                    return
            except usb.core.USBError as e:
                _logger.debug(e)
            _logger.warning("Device has DFU interface, "
                            "but has no DFU functional descriptor")

            # fake version 1.0
            func_dfu = FuncDescriptor(
                bLength=7,
                bcdDFUVersion=0x0100
            )

            # goto found_dfu
            _found_dfu(dev, cfg, func_dfu)
            return


__all__ = (
    'IFF',
    'DfuUtil',
    'MAX_DESC_STR_LEN',
    'probe_devices',
    'disconnect_devices',
    'print_dfu_if',
    'list_dfu_interfaces',
)

if __name__ == '__main__':
    import logging

    _logger.setLevel(logging.DEBUG)
    _ctx = usb.core.find(find_all=True, idVendor=0x1fc9)
    probe_devices(_ctx)
    list_dfu_interfaces()
    disconnect_devices()

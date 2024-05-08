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

from dataclasses import dataclass, field
from typing import Generator

from pydfuutil.dfu import DfuIf, Mode
import usb.core

from pydfuutil.logger import logger

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

MAX_DESC_STR_LEN = 253
MAX_PATH_LEN = 20


@dataclass
class DfuUtil:
    dfu_if: DfuIf
    match_path: str
    match_vendor: int
    match_product: int
    match_vendor_dfu: int
    match_product_dfu: int
    match_config_index: int
    match_iface_index: int
    match_iface_alt_index: int
    match_devnum: int
    match_iface_alt_name: str
    match_serial: str
    match_serial_dfu: str

    dfu_root: DfuIf = None

    path_buf: str = None


def find_descriptor():
    raise NotImplementedError


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

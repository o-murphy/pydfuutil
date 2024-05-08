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
from pydfuutil.dfu import DfuIf, Mode

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

    path_buf: bytearray = field(
        default_factory=lambda: bytearray(MAX_PATH_LEN)
    )


def find_descriptor():
    raise NotImplementedError


def get_utf8_string_descriptor():
    raise NotImplementedError


def get_string_descriptor_ascii():
    raise NotImplementedError


def probe_configuration():
    raise NotImplementedError


def get_path():
    raise NotImplementedError


def probe_devices():
    raise NotImplementedError


def disconnect_devices():
    raise NotImplementedError


def print_dfu_if():
    raise NotImplementedError


# Walk the device tree and print out DFU devices
def list_dfu_interfaces():
    raise NotImplementedError


__all__ = (
    'Mode',
    'MAX_DESC_STR_LEN',
    'probe_devices',
    'disconnect_devices',
    'print_dfu_if',
    'list_dfu_interfaces',
)

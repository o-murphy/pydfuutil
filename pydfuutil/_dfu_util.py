"""
Functions for detecting DFU USB entities
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
import usb.core
from usb import DT_STRING

from pydfuutil.dfu import DfuIf, Mode
from pydfuutil.logger import logger
from pydfuutil.usb_dfu import USB_DT_DFU

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


match_path = None
match_vendor = -1
match_product = -1
match_vendor_dfu = -1
match_product_dfu = -1
match_config_index = -1
match_iface_index = -1
match_iface_alt_index = -1
match_devnum = -1
match_iface_alt_name = None
match_serial = None
match_serial_dfu = None


def find_descriptor(desc_list: list[int], desc_type: int, res_buf: bytearray) -> int:
    """
    Look for a descriptor in a concatenated descriptor list. Will
    return upon the first match of the given descriptor type. Returns length of
    found descriptor, limited to res_size
    :param desc_list:
    :param desc_type:
    :param res_buf:
    :return:
    """
    p = 0
    list_len = len(desc_list)
    res_size = len(res_buf)

    if list_len < 2:
        return -1

    while p + 1 < list_len:
        desclen = desc_list[p]
        if desclen == 0:
            _logger.warning("Invalid descriptor list")
            return -1
        if desc_list[p + 1] == desc_type:
            if desclen > res_size:
                desclen = res_size
            if p + desclen > list_len:
                desclen = list_len - p
            res_buf[:desclen] = desc_list[p:p + desclen]
            return desclen
        p += desc_list[p]
    return -1


def get_utf8_string_descriptor(dev: usb.core.Device, desc_index: int,
                               data: bytearray, length: int) -> [bytes, None]:
    # get the language IDs and pick the first one
    r = usb.util.get_string(dev, 0, 0)
    if not r:
        _logger.warning("Failed to retrieve language identifiers")
        return None
    tbuf = r.encode("utf-16-le")

    # must have at least one ID
    if len(tbuf) < 4 or tbuf[0] < 4 or tbuf[1] != DT_STRING:
        _logger.warning("Broken LANGID string descriptor")
        return None

    langid = tbuf[2] | tbuf[3] << 8

    r = usb.util.get_string(dev, desc_index, langid)
    if not r:
        _logger.warning(f"Failed to retrieve string descriptor {desc_index}")
        return None
    tbuf = r.encode('utf-16-le')
    if len(tbuf) < 2 or tbuf[0] < 2:
        _logger.warning(f"String descriptor {desc_index} too short")
        return None
    if tbuf[1] != DT_STRING:  # sanity check
        _logger.warning(f"Malformed string descriptor {desc_index}, type 0x{tbuf[1]:02X}")
        return None
    if tbuf[0] > r:  # if short read
        _logger.warning(f"Patching string descriptor {desc_index} "
                        f"length (was {tbuf[0]}, received {len(r)})")
        tbuf[0] = r  # fix up descriptor length

    outlen = tbuf[0] - 2
    if length < outlen:
        outlen = length

    data[:outlen] = tbuf[2:2 + outlen]

    return data


def get_string_descriptor_ascii(dev: usb.core.Device, desc_index: int,
                                data: bytearray, length: int) -> [bytes, None]:
    buf = bytearray(255)
    r = get_utf8_string_descriptor(dev, desc_index, buf, length)
    if not r:
        return None

    # convert from 16-bit unicode to ascii string
    return data.decode("ascii").encode('ascii')


def probe_configuration(dev: usb.core.Device):

    for cfg in dev.configurations():
        has_dfu = 0

        if match_config_index > -1 and match_config_index != cfg.bConfigurationValue:
            continue

        # In some cases, noticably FreeBSD if uid != 0
        # the configuration descriptors are empty

        if not cfg:
            return

        ret  = find_descriptor(cfg.extra, USB_DT_DFU)



__all__ = (
    'DfuIf',
    'Mode',
    'match_path',
    'match_vendor',
    'match_product',
    'match_vendor_dfu',
    'match_product_dfu',
    'match_config_index',
    'match_iface_index',
    'match_iface_alt_index',
    'match_devnum',
    'match_iface_alt_name',
    'match_serial',
    'match_serial_dfu',
    'probe_devices',
    'disconnect_devices',
    'print_dfu_if',
    'list_dfu_interfaces',
)

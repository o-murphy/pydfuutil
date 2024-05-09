"""
Simple quirk system for dfu-util
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
from enum import IntEnum, IntFlag

from pydfuutil.dfuse_mem import MemSegment, find_segment
from pydfuutil.logger import logger

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])

# Fallback value, works for OpenMoko
DEFAULT_POLLTIMEOUT = 5
GD32VF103_FLASH_BASE = 0x08000000


class VENDOR(IntEnum):
    """Vendor IDs"""
    OPENMOKO = 0x1d50  # Openmoko Freerunner / GTA02
    FIC = 0x1d50  # Openmoko Freerunner / GTA02
    VOTI = 0x16c0  # OpenPCD Reader
    LEAFLABS = 0x1eaf  # Maple
    SIEMENS = 0x0908  # Siemens AG
    MIDIMAN = 0x0763  # Midiman
    GIGADEVICE = 0x28e9  # GigaDevice


class PRODUCT(IntEnum):
    """Product IDs"""
    FREERUNNER_FIRST = 0x5117
    FREERUNNER_LAST = 0x5126
    SIMTRACE = 0x0762
    OPENPCD = 0x076b
    OPENPICC = 0x076c
    MAPLE3 = 0x0003  # rev 3 and 5
    PXM40 = 0x02c4  # Siemens AG, PXM 40
    PXM50 = 0x02c5  # Siemens AG, PXM 50
    TRANSIT = 0x2806  # M-Audio Transit (Midiman)
    GD32 = 0x0189  # GigaDevice GD32VF103 rev 1


class QUIRK(IntFlag):
    """Quirk flags"""
    POLLTIMEOUT = 1 << 0
    FORCE_DFU11 = 1 << 1
    UTF8_SERIAL = 1 << 2
    DFUSE_LAYOUT = 1 << 3
    DFUSE_LEAVE = 1 << 4


# pylint: disable=invalid-name
def get_quirks(vendor: int, product: int, bcdDevice: int) -> [int, QUIRK]:
    """
    Get device specific quirks
    :param vendor: VID
    :param product: PID
    :param bcdDevice:
    :return: device specific quirks
    """
    quirks = 0

    # Device returns bogus bwPollTimeout values
    if vendor in {VENDOR.OPENMOKO, VENDOR.FIC} and \
            PRODUCT.FREERUNNER_FIRST <= product <= PRODUCT.FREERUNNER_LAST:
        quirks |= QUIRK.POLLTIMEOUT

    if vendor == VENDOR.VOTI and \
            product in {PRODUCT.OPENPCD, PRODUCT.SIMTRACE, PRODUCT.OPENPICC}:
        quirks |= QUIRK.POLLTIMEOUT

    # Reports wrong DFU version in DFU descriptor
    if vendor == VENDOR.LEAFLABS and \
            product == PRODUCT.MAPLE3 and \
            bcdDevice == 0x0200:
        quirks |= QUIRK.FORCE_DFU11

    # old devices(bcdDevice == 0) return bogus bwPollTimeout values
    if vendor == VENDOR.SIEMENS and \
            product in {PRODUCT.PXM40, PRODUCT.PXM50} and \
            bcdDevice == 0:
        quirks |= QUIRK.POLLTIMEOUT

    # M-Audio Transit returns bogus bwPollTimeout values
    if vendor == VENDOR.MIDIMAN and \
            product == PRODUCT.TRANSIT:
        quirks |= QUIRK.POLLTIMEOUT

    # Some GigaDevice GD32 devices have improperly-encoded serial numbers
    # and bad DfuSe descriptors which we use serial number to correct.
    # They also "leave" without a DFU_GETSTATUS request
    if vendor == VENDOR.GIGADEVICE and \
            product == PRODUCT.GD32:
        quirks |= QUIRK.UTF8_SERIAL
        quirks |= QUIRK.DFUSE_LAYOUT
        quirks |= QUIRK.DFUSE_LEAVE

    return quirks


def fixup_dfuse_layout(dif, segment_list: MemSegment):
    """fixup dfuse layout for specific device"""
    if (dif.vendor == VENDOR.GIGADEVICE and
            dif.product == PRODUCT.GD32 and
            dif.altsetting == 0 and
            dif.serial_name and
            len(dif.serial_name) == 4 and
            dif.serial_name[0] == '3' and
            dif.serial_name[3] == 'J'):

        _logger.info("Found GD32VF103, which reports a bad page size "
                     "and count for its internal memory.")

        seg = find_segment(segment_list, GD32VF103_FLASH_BASE)
        if not seg:
            _logger.error(f"Could not fix GD32VF103 layout "
                          f"because there is no segment at {GD32VF103_FLASH_BASE}")
            return

        # All GD32VF103 have this page size, according to Nucleisys's dfu-util
        seg.pagesize = 1024

        # From Tables 2-1 and 2-2 ("devices features and peripheral list")
        # in the GD32VF103 Datasheet
        if dif.serial_name[2] == 'B':
            count = 128
        elif dif.serial_name[2] == '8':
            count = 64
        elif dif.serial_name[2] == '6':
            count = 32
        elif dif.serial_name[2] == '4':
            count = 16
        else:
            logger.warning(f"Unknown flash size '{dif.serial_name[2]}' "
                           f"in part number; defaulting to 128KB.")
            count = 128

        seg.end = seg.start + (count * seg.pagesize) - 1

        logger.info(f"Fixed layout based on part number: page size {seg.pagesize}, count {count}.")


__all__ = (
    'VENDOR',
    'PRODUCT',
    'QUIRK',
    'DEFAULT_POLLTIMEOUT',
    'get_quirks',
    'fixup_dfuse_layout'
)

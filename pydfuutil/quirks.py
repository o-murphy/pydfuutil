"""
Simple quirk system for dfu-util
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

VENDOR_OPENMOKO = 0x1d50  # Openmoko Freerunner / GTA02
VENDOR_FIC = 0x1457  # Openmoko Freerunner / GTA02
VENDOR_VOTI = 0x16c0  # OpenPCD Reader
VENDOR_LEAFLABS = 0x1eaf  # Maple
PRODUCT_MAPLE3 = 0x0003  # rev 3 and 5

QUIRK_POLLTIMEOUT = 1 << 0
QUIRK_FORCE_DFU11 = 1 << 1

# Fallback value, works for OpenMoko
DEFAULT_POLLTIMEOUT = 5


def get_quirks(vendor: int, product: int, bcdDevice: int) -> int:
    quirks = 0

    # Device returns bogus bwPollTimeout values
    if vendor == VENDOR_OPENMOKO or vendor == VENDOR_FIC or vendor == VENDOR_VOTI:
        quirks |= QUIRK_POLLTIMEOUT

    # Reports wrong DFU version in DFU descriptor
    if vendor == VENDOR_LEAFLABS and product == PRODUCT_MAPLE3 and bcdDevice == 0x0200:
        quirks |= QUIRK_FORCE_DFU11

    return quirks

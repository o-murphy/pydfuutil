"""
USB string descriptor should contain max 126 UTF-16 characters
but 254 would even accommodate a UTF-8 encoding + NUL terminator
"""

from pydfuutil.dfu import DfuIf, Mode


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
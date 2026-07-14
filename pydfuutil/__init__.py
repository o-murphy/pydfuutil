"""
PyDfuUtil - Pure python fork of **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**
wrappers to **[libusb](https://github.com/libusb/libusb)
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

from __future__ import annotations

import logging

__author__ = "o-murphy"
__credits__ = ("Dmytro Yaroshenko",)
__copyright__ = ('2023 Yaroshenko Dmytro (https://github.com/o-murphy)',)

_logger = logging.getLogger(__name__)

# Resolved libusb1 backend, shared across the package so every
# usb.core.find() call goes through the SAME loaded libusb instance.
# None means "let pyusb search for a system libusb itself" — a valid,
# supported value for the `backend=` kwarg of usb.core.find().
DEFAULT_BACKEND = None

try:
    import libusb_package
    from usb.backend import libusb1

    try:
        DEFAULT_BACKEND = libusb1.get_backend(find_library=libusb_package.find_library)
    except Exception as e:
        _logger.warning(
            f"Failed to load libusb backend via libusb_package: {e}. "
            "Falling back to pyusb's own system search."
        )
    if DEFAULT_BACKEND is None:
        _logger.warning(
            "libusb_package is installed but no bundled libusb library was "
            "found through it; falling back to pyusb's own system search."
        )
except ImportError:
    _logger.debug(
        "libusb_package not installed; pyusb will search for a system "
        "libusb itself. Install the 'libusb' extra "
        "(pip install pydfuutil[libusb]) for a bundled, "
        "platform-independent libusb binary."
    )

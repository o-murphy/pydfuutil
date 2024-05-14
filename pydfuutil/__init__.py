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

__author__ = "o-murphy"
__credits__ = ("Dmytro Yaroshenko",)
__copyright__ = ('2023 Yaroshenko Dmytro (https://github.com/o-murphy)',)

try:
    import libusb_package
    from usb.backend import libusb1
    libusb1.get_backend(libusb_package.find_library)
    # # TODO: test it
    # # prevent raising USBError to got error codes directly
    # # on libusb1 backend
    # usb.backend.libusb1._check = lambda x: x
finally:
    pass

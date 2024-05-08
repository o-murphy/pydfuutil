"""
PyDfuUtil - Pure python fork of **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**
wrappers to **[libusb](https://github.com/libusb/libusb)
"""

__author__ = "o-murphy"
__credits__ = ["Dmytro Yaroshenko"]
__copyright__ = ('2023 Yaroshenko Dmytro (https://github.com/o-murphy)',)


try:
    import libusb_package
    from usb.backend import libusb1

    libusb1.get_backend(libusb_package.find_library)
finally:
    pass

import enum

import libusb_package
import usb.core
import usb.util
import usb.backend.libusb1

MAX_DESC_STR_LEN = 255

#
DFU_IFF_DFU  = 0x0001
# USB_DT_DFU	= DESC_TYPE_DFU	=	0x21
USB_DT_DFU	= DESC_TYPE_DFU	=	0x4
#

class Mode(enum.IntEnum):
        MODE_NONE = enum.auto()
        MODE_VERSION = enum.auto()
        MODE_LIST = enum.auto()
        MODE_DETACH = enum.auto()
        MODE_UPLOAD = enum.auto()
        MODE_DOWNLOAD = enum.auto()


dfu_root = None

match_bus = -1
match_device = -1
match_vendor = -1
match_product = -1
match_vendor_dfu = -1
match_product_dfu = -1
match_config_index = -1
match_iface_index = -1
match_iface_alt_index = -1
match_iface_alt_name = None
match_serial = None
match_serial_dfu = None

mode = Mode.MODE_NONE
expected_size = 0
transfer_size = 0
final_reset = 0
dfuse_device = 0
dfuse_options = None
detach_delay = 5

def probeConfig(dev, desc):
    func_dfu = None
    devh = None
    pdfu = None
    cfg = None

    for cfg_idx in range(dev.bNumConfigurations):

        cfg = desc


        print(hex(dev.idProduct), desc.bDescriptorType)
        func_dfu = usb.util.find_descriptor(
            desc,
            # custom_match=lambda d: d.bDescriptorType == usb.util.DESC_TYPE_DFU
            custom_match=lambda d: d.bDescriptorType == USB_DT_DFU
        )

        if func_dfu is not None:
            break

        # print(dev[cfg_idx])
        print(dev)

        # cfg = dev[0].configurations[cfg_idx]
        # cfg = desc

        for intf in cfg.interfaces():
            if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
                continue

            alt = usb.util.find_descriptor(
                intf,
                custom_match=lambda d: d.bDescriptorType == USB_DT_DFU
            )

            if alt is not None:
                func_dfu = usb.util.find_descriptor(
                    alt,
                    custom_match=lambda d: d.bDescriptorType == USB_DT_DFU
                )

                if func_dfu is not None:
                    break

            if func_dfu is not None:
                break


        if func_dfu is not None:
            break

    if func_dfu is not None:
        # Retrieve additional information about the device and interface
        if func_dfu.bLength == 7:
            print("Deducing device DFU version from functional descriptor length")
            func_dfu.bcdDFUVersion = 0x0100
        elif func_dfu.bLength < 9:
            print("Error obtaining DFU functional descriptor")
            print("Please report this as a bug!")
            print("Warning: Assuming DFU version 1.0")
            func_dfu.bcdDFUVersion = 0x0100
            print("Warning: Transfer size can not be detected")
            func_dfu.wTransferSize = 0

        for intf in cfg.interfaces():
            if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
                continue


            #
            # print(intf)
            #
            # dfu_mode = intf.bInterfaceProtocol == 2
            #
            # if func_dfu.bcdDFUVersion == 0x011a and intf.bInterfaceProtocol == 0:
            #     dfu_mode = True
            #
            # if dfu_mode:
            #     if (match_vendor_dfu >= 0 and match_vendor_dfu != desc.idVendor) or \
            #        (match_product_dfu >= 0 and match_product_dfu != desc.idProduct):
            #         continue
            # else:
            #     if (match_vendor >= 0 and match_vendor != desc.idVendor) or \
            #        (match_product >= 0 and match_product != desc.idProduct):
            #         continue
            dfu_mode = True

            devh = dev

            alt_name = "UNKNOWN"
            serial_name = "UNKNOWN"

            if intf.iInterface != 0:
                try:
                    alt_name = usb.util.get_string(devh, intf.iInterface)
                except usb.core.USBError:
                    pass

            if devh.iSerialNumber != 0:
                try:
                    serial_name = usb.util.get_string(devh, devh.iSerialNumber)
                except usb.core.USBError:
                    pass

            if dfu_mode and match_iface_alt_name is not None and alt_name != match_iface_alt_name:
                continue

            if dfu_mode and match_serial_dfu is not None and serial_name != match_serial_dfu:
                continue
            # pdfu = {
            #     'func_dfu': func_dfu,
            #     'dev': dev,
            #     'vendor': devh.idVendor,
            #     'product': devh.idProduct,
            #     'bcdDevice': devh.bcdDevice,
            #     'configuration': cfg.bConfigurationValue,
            #     'interface': intf.bInterfaceNumber,
            #     'altsetting': intf.bAlternateSetting,
            #     # 'devnum': dev.devnum,
            #     # 'busnum': dev.busnum,
            #     'alt_name': alt_name,
            #     'serial_name': serial_name,
            #     'flags': DFU_IFF_DFU if dfu_mode else 0,
            #     'bMaxPacketSize0': desc.bMaxPacketSize0
            # }

            pdfu = {
                'func_dfu': func_dfu,
                'dev': dev,
                'vendor': devh.idVendor,
                'product': devh.idProduct,
                'bcdDevice': devh.bcdDevice,
                'configuration': cfg.bConfigurationValue,
                'interface': intf.bInterfaceNumber,
                # Add more attributes as needed
            }

            return pdfu
            # Add pdfu to your desired data structure or process it accordingly

    if cfg is not None:
        usb.util.dispose_resources(dev)

# Usage

libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
devices = usb.core.find(find_all=True, backend=libusb1_backend, idVendor=0x1FC9, idProduct=0x000C)

for dev in devices:
# if dev is not None:
    desc = usb.util.find_descriptor(dev)
    print(hex(dev.idProduct))
    print(probeConfig(dev, desc))


import libusb_package
import usb.backend.libusb1
import usb.core
# from pyfu_usb.descriptor import *


DFU_DETACH = 0
DFU_DNLOAD = 1
DFU_UPLOAD = 2
DFU_GETSTATUS = 3
DFU_CLRSTATUS = 4
DFU_GETSTATE = 5
DFU_ABORT = 6

dfu_timeout = 5000


def dfu_get_status(device: usb.core.Device, interface):

    buffer = bytes(6)

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFU_GETSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=buffer,
        # wLength=length,
        timeout=dfu_timeout,
    )
    print('result', result)
    buffer = result.tobytes()
    # if result == 6:
    print('bStatus', buffer[0])
    print('bwPollTimeout', ((0xff & buffer[3]) << 16) | ((0xff & buffer[2]) << 8) | (0xff & buffer[1]))

    print('bState', buffer[4])
    print('iString', buffer[5])


def dfu_upload(device: usb.core.Device, interface, length, transaction, data):
    """
    Upload data from the device using PyUSB library.

    Args:
        device: PyUSB device handle.
        interface: USB device interface.
        length: Length of the data to upload.
        transaction: Transaction counter.
        data: Data buffer to store the uploaded data.

    Returns:
        The status of the control transfer.
    """
    status = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFU_UPLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data,
        # wLength=length,
        timeout=dfu_timeout,
    )

    return status


USB_DT_DFU = 0x21

# def found_dfu():
"""
struct dfu_if {
    struct usb_dfu_func_descriptor func_dfu;
    uint16_t quirks;
    uint16_t busnum;
    uint16_t devnum;
    uint16_t vendor;
    uint16_t product;
    uint16_t bcdDevice;
    uint8_t configuration;
    uint8_t interface;
    uint8_t altsetting;
    uint8_t flags;
    uint8_t bMaxPacketSize0;
    char *alt_name;
    char *serial_name;
    libusb_device *dev;
    libusb_device_handle *dev_handle;
    struct dfu_if *next;
};"""


libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(backend=libusb1_backend, idVendor=0x1FC9, idProduct=0x000C)
desc = usb.util.find_descriptor(dev)

# print(dev)
# print(desc)
# print(desc.interfaces()[0].__dir__())
# print(desc.interfaces()[0].alternate_index)
# print(desc.interfaces()[0].index)
# print(desc.interfaces()[0].configuration)
print([hex(i) for i in desc.interfaces()[0].extra_descriptors])

# dev.reset()

ext = usb.util.find_descriptor(
                desc.interfaces()[0].extra_descriptors,
                custom_match=lambda d: d == USB_DT_DFU
            )

print('ext', ext)




offset = 532480
start = int((offset + 4096) / 2048)
print(start)

intf = usb.util.find_descriptor(
                dev[0],
                custom_match=lambda d: d.bDescriptorType == 0x4
            )
print(intf)

"""
struct usb_dfu_func_descriptor {
	uint8_t		bLength;
	uint8_t		bDescriptorType;
	uint8_t		bmAttributes;
#define USB_DFU_CAN_DOWNLOAD	(1 << 0)
#define USB_DFU_CAN_UPLOAD	(1 << 1)
#define USB_DFU_MANIFEST_TOL	(1 << 2)
#define USB_DFU_WILL_DETACH	(1 << 3)
	uint16_t		wDetachTimeOut;
	uint16_t		wTransferSize;
	uint16_t		bcdDFUVersion;
#ifdef _MSC_VER
};
"""

# Retrieve additional information about the device and interface
if intf.bLength == 7:
    print("Deducing device DFU version from functional descriptor length")
    intf.bcdDFUVersion = 0x0100
elif intf.bLength < 9:
    print("Error obtaining DFU functional descriptor")
    print("Please report this as a bug!")
    print("Warning: Assuming DFU version 1.0")
    intf.bcdDFUVersion = 0x0100
    print("Warning: Transfer size can not be detected")
    intf.wTransferSize = 0

for intf in desc.interfaces():
    if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
        continue

    dfu_mode = intf.bInterfaceProtocol == 2
    # print('bcdDFUVersion', intf.bcdDFUVersion)

# intf.bcdDFUVersion = 0x011a
# intf.bInterfaceProtocol = 0


dfu_get_status(dev, intf.bInterfaceNumber)


# data = bytes(2048)
#
#
# print(intf.bInterfaceNumber)
#
# # a = dfu_upload(dev, intf.iInterface, 2048, start, 2048 + offset)
# # a = dfu_upload(dev, intf.bInterfaceNumber, 2048, start, data)
# a = dfu_upload(dev, intf.bInterfaceNumber, 2048, start, data)
# print(a.tobytes())
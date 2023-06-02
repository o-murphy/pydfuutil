from pydfuutil.dfu import *
import libusb_package
import usb.backend.libusb1
import usb.core
from time import sleep


dfu_timeout = 5000


USB_DT_DFU = 0x21


def get_dev_h():
    libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    devh = usb.core.find(backend=libusb1_backend, idVendor=0x1FC9, idProduct=0x000C)
    return devh


def get_dev_descriptor(devh):
    desc = usb.util.find_descriptor(devh)
    return desc


def get_intf_descriptor(devh: usb.core.Device, desc, intf_idx: int) -> usb.core.Interface:
    return desc.interfaces()[intf_idx]


def get_intf_extra(intf: usb.core.Interface, match=USB_DT_DFU):
    print(f'Extra found: {len(intf.extra_descriptors)}')

    ext = usb.util.find_descriptor(
        intf.extra_descriptors,
        custom_match=lambda d: d == match
    )
    return ext



if __name__ == '__main__':
    # offset = 532480
    # start = int((offset + 4096) / 2048)
    # data = bytes(2048)
    #
    # # intf: usb.core.Interface = usb.util.find_descriptor(
    # #                 dev[0],
    # #                 custom_match=lambda d: d.bDescriptorType == 0x4
    # #             )
    # # print(intf)
    #
    # devh = get_dev_h()
    # print(devh)
    #
    # desc = get_dev_descriptor(devh)
    # intf = get_intf_descriptor(devh, desc, 0)
    #
    # _, status = dfu_get_status(devh, intf.bInterfaceNumber)
    # print(status)
    #
    #
    # usb.util.claim_interface(devh, intf.bInterfaceNumber)
    # dfu_detach(devh, intf.bInterfaceNumber, 1000)
    # usb.util.release_interface(devh, intf.bInterfaceNumber)
    #
    # _, status = dfu_get_status(devh, intf.bInterfaceNumber)
    #
    # print(status)
    #
    #
    # # dfu_clear_status(devh, intf.bInterfaceNumber)
    #
    #
    # dfu_get_status(devh, intf.bInterfaceNumber)
    #
    # print(dfu_get_state(devh, intf.bInterfaceNumber))
    #
    # # a = dfu_upload(devh, intf.bInterfaceNumber, start, data)
    # # print(a.tobytes())
    #
    # # setalt = intf.set_altsetting()

    INTERFACE_NUMBER = 0
    dev: usb.core.Device = get_dev_h()
    print(dev)

    # if dev.is_kernel_driver_active(INTERFACE_NUMBER):
    #     dev.detach_kernel_driver(INTERFACE_NUMBER)

    # Set the active configuration
    dev.set_configuration()

    # Claim the interface
    usb.util.claim_interface(dev, INTERFACE_NUMBER)

    # # Control transfer to read the iSerialNumber
    # response = dev.ctrl_transfer(
    #     bmRequestType=usb.util.CTRL_TYPE_STANDARD | usb.util.CTRL_IN,
    #     bRequest=0x06,
    #     wValue=(usb.util.DESC_TYPE_STRING << 8) | 0x00,
    #     wIndex=INTERFACE_NUMBER,
    #     data_or_wLength=255,
    # )

    response = usb.control.get_descriptor(dev, desc_type=0x1, desc_size=0x12, desc_index=INTERFACE_NUMBER)
    print(response)
    # Convert the response to a string
    serial_number = response[2:].tobytes().decode("utf-16le")
    serial_number = response.tobytes().decode("utf-16le")

    # Release the interface and close the device
    usb.util.release_interface(dev, INTERFACE_NUMBER)
    usb.util.dispose_resources(dev)

    print("iSerialNumber:", serial_number)

    # # Detach the kernel driver if active
    # if dev.is_kernel_driver_active(INTERFACE_NUMBER):
    #     dev.detach_kernel_driver(INTERFACE_NUMBER)

    # # Set the active configuration
    # dev.set_configuration()
    #
    # desc = usb.control.get_descriptor(
    #     dev, desc_type=0x1, desc_size=0x12, desc_index=INTERFACE_NUMBER)
    #
    # print(desc.tobytes().decode('utf-8', errors='ignore'))

    # # dev.ctrl_transfer(
    #     usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_STANDARD | usb.util.D
    # # )
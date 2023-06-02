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


def get_intf_descriptor(devh: usb.core.Device, desc) -> usb.core.Interface:
    print(f'Inrf found: {len(desc.interfaces())}')
    return desc.interfaces()[0]


def get_intf_extra(intf):
    print(f'Extra found: {len(intf.extra_descriptors)}')

    ext = usb.util.find_descriptor(
        intf.extra_descriptors,
        custom_match=lambda d: d == USB_DT_DFU
    )
    return ext



if __name__ == '__main__':
    offset = 532480
    start = int((offset + 4096) / 2048)
    data = bytes(2048)

    # intf: usb.core.Interface = usb.util.find_descriptor(
    #                 dev[0],
    #                 custom_match=lambda d: d.bDescriptorType == 0x4
    #             )
    # print(intf)

    devh = get_dev_h()

    desc = get_dev_descriptor(devh)
    intf = get_intf_descriptor(devh, desc)

    _, status = dfu_get_status(devh, intf.bInterfaceNumber)
    print(status)


    usb.util.claim_interface(devh, intf.bInterfaceNumber)
    dfu_detach(devh, intf.bInterfaceNumber, 1000)
    usb.util.release_interface(devh, intf.bInterfaceNumber)

    _, status = dfu_get_status(devh, intf.bInterfaceNumber)

    print(status)


    # dfu_clear_status(devh, intf.bInterfaceNumber)


    dfu_get_status(devh, intf.bInterfaceNumber)

    print(dfu_get_state(devh, intf.bInterfaceNumber))

    # a = dfu_upload(devh, intf.bInterfaceNumber, start, data)
    # print(a.tobytes())

    # setalt = intf.set_altsetting()

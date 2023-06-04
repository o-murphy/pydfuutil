from time import sleep

import libusb_package

libusb_package

import usb.backend.libusb1
import usb.core

from pydfuutil.dfu import *

DFU_TIMEOUT = 5000

USB_DT_DFU = 0x21


class DFUDevice:
    def __init__(self, dev: usb.core.Device):
        self.dev = dev
        self.intf = 0x00

    def status(self) -> (int, dict):
        _, status = dfu_get_status(self.dev, self.intf)
        sleep(status.bwPollTimeout)
        return _, status

    def probe(self):

        cfg: usb.core.Configuration
        cfg = self.dev.get_active_configuration()  # or: for cfg in self.dev.configurations()
        if not cfg:
            return

        ret = tuple(usb.util.find_descriptor(
            cfg.extra_descriptors, find_all=True,
            custom_match=lambda d: d == USB_DT_DFU
        ))
        print('ret', not ret)
        if ret:
            pass
        else:

            intf: usb.core.Interface
            for intf in cfg.interfaces():
                if not intf:
                    break

                # usb.control.alt
                print(intf)


    def connect(self):
        ...

    def is_connect_valid(self):
        _, status = self.status()
        while status.bState != DFUState.DFU_IDLE:

            if status.bState in [DFUState.APP_IDLE, DFUState.APP_DETACH]:
                return False
            elif status.bState == DFUState.DFU_ERROR:
                if dfu_clear_status(self.dev, self.intf) < 0:
                    return False
                _, status = self.status()
            elif status.bState in [DFUState.DFU_DOWNLOAD_IDLE, DFUState.DFU_UPLOAD_IDLE]:
                if dfu_abort(self.dev, self.intf) < 0:
                    return False
                _, status = self.status()
            else:
                break

        if status.bStatus != DFUStatus.OK:
            if dfu_clear_status(self.dev, self.intf) < 0:
                return False
            _, status = self.status()
            if _ < 0:
                return False
            if status.bStatus != DFUStatus.OK:
                return False
            sleep(status.bwPollTimeout)

        return True


def get_dev_h():
    libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(backend=libusb1_backend, idVendor=0x1FC9, idProduct=0x000C)
    return dev


def get_dev_descriptor(dev):
    desc = usb.util.find_descriptor(dev)
    return desc


def get_intf_descriptor(dev: usb.core.Device, desc, intf_idx: int) -> usb.core.Interface:
    return desc.interfaces()[intf_idx]


def get_intf_extra(intf: usb.core.Interface, match=USB_DT_DFU):
    print(f'Extra found: {len(intf.extra_descriptors)}')

    ext = usb.util.find_descriptor(
        intf.extra_descriptors,
        custom_match=lambda d: d == match
    )
    return ext


if __name__ == '__main__':
    # dev = get_dev_h()
    dfudev = DFUDevice(get_dev_h())
    print(dfudev.is_connect_valid())

    print(dfudev.probe())

    # dfu_detach(dfudev.dev, dfudev.intf, 1000)
    #
    # dfudev.dev = None
    #
    # sleep(1)
    #
    # # dev = get_dev_h()
    # # dfudev = DFUDevice(dev)
    # # print(dfudev.is_connect_valid())
    #
    # dfudev.dev = get_dev_h()
    #
    # # dfu_clear_status(dfudev.dev, dfudev.intf)
    #
    # # s = dfudev.status()
    #
    # offset = 532480
    # start = int((offset + 4096) / 2048)
    # data = bytes(2048)

    # a = dfu_upload(dfudev.dev, dfudev.intf, start, data)
    # print(a)

    # usb.util.release_interface(dfudev.dev, 0)
    # usb.util.dispose_resources(dfudev.dev)
    # dfudev.dev = None
    #
    # dfudev.dev = get_dev_h()
    # s = dfudev.status()

    # print(dfu_clear_status(dfudev.dev, dfudev.intf))
    #
    # # dfu_detach(dfudev.dev, dfudev.intf, 1000)
    # dfu_clear_status(dfudev.dev, dfudev.intf)

    # dfudev.status()
    # # print(dfu_clear_status(dfudev.dev, dfudev.intf))
    #
    # dfudev.dev.reset()
    #
    # dfudev.status()
    # dfu_clear_status(dfudev.dev, dfudev.intf)
    #
    #
    #
    # try:
    #     bb = bytearray(a)
    #     bb[:3] = b'DFU'
    #     b = bytes(bb)
    #     b = dfu_download(dfudev.dev, dfudev.intf, start, b)
    #     print(b)
    # except Exception:
    #     pass
    #
    # dfu_clear_status(dfudev.dev, dfudev.intf)
    #
    #
    # print(dfu_upload(dfudev.dev, dfudev.intf, start, data))

    #
    # # intf: usb.core.Interface = usb.util.find_descriptor(
    # #                 dev[0],
    # #                 custom_match=lambda d: d.bDescriptorType == 0x4
    # #             )
    # # print(intf)
    #
    # dev = get_dev_h()
    # print(dev)
    #
    # desc = get_dev_descriptor(dev)
    # intf = get_intf_descriptor(dev, desc, 0)
    #
    # _, status = dfu_get_status(dev, intf.bInterfaceNumber)
    # print(status, dfu_state_to_string(status['bState']))
    #
    #
    # usb.util.claim_interface(dev, intf.bInterfaceNumber)
    # dfu_detach(dev, intf.bInterfaceNumber, 1000)
    # usb.util.release_interface(dev, intf.bInterfaceNumber)
    #
    # _, status = dfu_get_status(dev, intf.bInterfaceNumber)
    # print(status, dfu_state_to_string(status['bState']))
    #
    #
    # # reconnect
    # # dfu_clear_status(dev, intf.bInterfaceNumber)
    # # dev = get_dev_h()
    # # intf = get_intf_descriptor(dev, desc, 0)
    # _, status = dfu_get_status(dev, intf.bInterfaceNumber)
    # print(status, dfu_state_to_string(status['bState']))

    # # dfu_clear_status(dev, intf.bInterfaceNumber)
    #
    #
    # dfu_get_status(dev, intf.bInterfaceNumber)
    #
    # print(dfu_get_state(dev, intf.bInterfaceNumber))
    #
    # # a = dfu_upload(dev, intf.bInterfaceNumber, start, data)
    # # print(a.tobytes())
    #
    # # setalt = intf.set_altsetting()

    # INTERFACE_NUMBER = 0
    # dev: usb.core.Device = get_dev_h()
    # print(dev)
    #
    # # if dev.is_kernel_driver_active(INTERFACE_NUMBER):
    # #     dev.detach_kernel_driver(INTERFACE_NUMBER)
    #
    # # Set the active configuration
    # dev.set_configuration()
    #
    # # Claim the interface
    # usb.util.claim_interface(dev, INTERFACE_NUMBER)

    # # Control transfer to read the iSerialNumber
    # response = dev.ctrl_transfer(
    #     bmRequestType=usb.util.CTRL_TYPE_STANDARD | usb.util.CTRL_IN,
    #     bRequest=0x06,
    #     wValue=(usb.util.DESC_TYPE_STRING << 8) | 0x00,
    #     wIndex=INTERFACE_NUMBER,
    #     data_or_wLength=255,
    # )

    # response = usb.control.get_descriptor(dev, desc_type=0x1, desc_size=0x12, desc_index=INTERFACE_NUMBER)
    # print(response)
    # # Convert the response to a string
    # serial_number = response[2:].tobytes().decode("utf-16le")
    # serial_number = response.tobytes().decode("utf-16le")

    # STRING_INDEX = 0x03
    #
    # new_string = "TSA9 #0000001"
    #
    # existing_string = usb.util.get_string(dev, 0x03)
    # print("iSerialNumber:", existing_string)
    #
    # # usb.util.set_string(dev, 0x03, "TSA9 #0000001")
    #
    # dev.ctrl_transfer(
    #     bmRequestType=usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
    #     bRequest=0x80,  # Custom request code for setting the string
    #     wValue=STRING_INDEX,
    #     wIndex=0,
    #     data_or_wLength=new_string.encode("utf-16le"),
    # )
    #
    # print("iSerialNumber:", usb.util.get_string(dev, 0x03))
    #
    # # Release the interface and close the device
    # usb.util.release_interface(dev, INTERFACE_NUMBER)
    # usb.util.dispose_resources(dev)
    #
    #
    #
    #
    # # # Detach the kernel driver if active
    # # if dev.is_kernel_driver_active(INTERFACE_NUMBER):
    # #     dev.detach_kernel_driver(INTERFACE_NUMBER)
    #
    # # # Set the active configuration
    # # dev.set_configuration()
    # #
    # # desc = usb.control.get_descriptor(
    # #     dev, desc_type=0x1, desc_size=0x12, desc_index=INTERFACE_NUMBER)
    # #
    # # print(desc.tobytes().decode('utf-8', errors='ignore'))
    #
    # # # dev.ctrl_transfer(
    # #     usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_STANDARD | usb.util.D
    # # # )

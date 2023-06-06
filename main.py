import logging
from time import sleep

import libusb_package
import usb.backend.libusb1
import usb.core
from construct import Struct, Int8ul, Byte, FlagsEnum, Int16ul, lib

from pydfuutil import dfu
from pydfuutil.usb_dfu import USB_DT_DFU, USB_DFU_FUNC_DESCRIPTOR

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

lib.setGlobalPrintFalseFlags(True)

# dfu.DFU_TIMEOUT = 5000
dfu.dfu_init(5000)


class DFUDevice:
    def __init__(self, dev: usb.core.Device):
        self.dev = dev
        self.intf = 0x00

    def status(self) -> (int, dict):
        _, status = dfu.dfu_get_status(self.dev, self.intf)
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
        while status.bState != dfu.DFUState.DFU_IDLE:

            if status.bState in [dfu.DFUState.APP_IDLE, dfu.DFUState.APP_DETACH]:
                return False
            elif status.bState == dfu.DFUState.DFU_ERROR:
                if dfu.dfu_clear_status(self.dev, self.intf) < 0:
                    return False
                _, status = self.status()
            elif status.bState in [dfu.DFUState.DFU_DOWNLOAD_IDLE, dfu.DFUState.DFU_UPLOAD_IDLE]:
                if dfu.dfu_abort(self.dev, self.intf) < 0:
                    return False
                _, status = self.status()
            else:
                break

        if status.bStatus != dfu.DFUStatus.OK:
            if dfu.dfu_clear_status(self.dev, self.intf) < 0:
                return False
            _, status = self.status()
            if _ < 0:
                return False
            if status.bStatus != dfu.DFUStatus.OK:
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
    dev = None
    dfudev = None
    while dev is None:
        dev = get_dev_h()
        dfudev = DFUDevice(dev)

    print(dev)

    intf = dev.get_active_configuration().interfaces()[0]
    extra = intf.extra_descriptors
    dfu_desc = USB_DFU_FUNC_DESCRIPTOR.parse(bytes(extra))
    print(dfu_desc)

    # dev.set_interface_altsetting()

    if not dfudev.is_connect_valid():
        dfu.dfu_detach(dfudev.dev, dfudev.intf, int(dfu_desc.wDetachTimeOut / 1000))
        dfudev.status()
        sleep(2)

        logger.debug('FREE DEVICE')
        dev = None
        dfudev = None

        logger.debug('Waiting for reconnect...')
        while dev is None:
            dev = get_dev_h()
            dfudev = DFUDevice(dev)
        logger.debug('Connecting...')

    dfudev.is_connect_valid()

    offset = 532480
    start = int((offset + 4096) / 2048)
    data = bytes(2048)

    a = dfu.dfu_upload(dfudev.dev, dfudev.intf, start, data)
    # dfu.dfu_upload(dfudev.dev, dfudev.intf, start, 0)
    logger.info(f'UPLOADED: {a[:10]}... (length: {len(a)}, truncated)')

    dfudev.is_connect_valid()
    dfudev.status()

    a = bytearray(a)
    a[:5] = b'VASYA'

    try:
        # cfg = dfudev.dev.get_active_configuration()
        #
        # intf: usb.core.Interface = cfg.interfaces()[0]
        # intf.set_altsetting()

        b = dfu.dfu_download(dfudev.dev, dfudev.intf, start, bytes(a))
        # dfu.dfu_download(dfudev.dev, dfudev.intf, start, 0)
        # print(b)
    except Exception as exc:
        logger.error(exc)
        dfudev.status()

        dfu.dfu_abort(dfudev.dev, dfudev.intf)

    dfudev.status()

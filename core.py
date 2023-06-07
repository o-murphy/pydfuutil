import copy
import logging
from time import sleep
from typing import Generator

import libusb_package
from usb.backend import libusb1
import usb.core

from pydfuutil import dfu

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


libusb1.get_backend(libusb_package.find_library)


def find(find_all=False, backend = None, custom_match = None, **args):
    dev = usb.core.find(find_all, backend, custom_match, **args)

    def device_iter():
        for d in dev:
            d = copy.copy(d)
            d.__class__ = DfuDevice
            yield d

    if dev is None:
        return dev
    elif isinstance(dev, usb.core.Device):
        dev = copy.copy(dev)
        dev.__class__ = DfuDevice
        return dev
    elif isinstance(dev, Generator):
        return device_iter()


class DfuDevice(usb.core.Device):

    @property
    def is_connect_valid(self):
        return

    @property
    def get_status(self) -> (int, dict):
        _, status = dfu.dfu_get_status(self, intf)
        sleep(status.bwPollTimeout)
        return _, status

    def probe(self):
        ...

    def connect(self):
        ...

    def disconnect(self):
        ...

    def reconnect(self):
        ...

    def get_dfu_descriptor(self):
        ...

    def get_dfu_interface(self):
        ...

    def do_upload(self):
        ...

    def do_download(self):
        ...





dfudev = DfuDevice()
cfg: usb.core.Configuration = dfudev.get_active_configuration()
intf: usb.core.Interface = cfg.interfaces()[0]


import copy
import logging
import math
from time import sleep
from typing import Generator

import construct
import libusb_package
import usb.core
from rich import progress
from usb.backend import libusb1

from progress import DfuProgress
from pydfuutil import dfu
from pydfuutil.usb_dfu import USB_DFU_FUNC_DESCRIPTOR

# setting global params
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# dfu.logger.setLevel(logging.INFO)

_progress_bar = DfuProgress(
    progress.TextColumn("[progress.description]{task.description}"),
    progress.BarColumn(20),
    progress.TaskProgressColumn(),
    progress.TimeRemainingColumn(),
    progress.DownloadColumn(),
    progress.TransferSpeedColumn(),
)

construct.lib.setGlobalPrintFalseFlags(True)

libusb1.get_backend(libusb_package.find_library)


def find(find_all=False, backend=None, custom_match=None, **args):
    dev = usb.core.find(find_all, backend, custom_match, **args)

    def device_iter():
        for d in dev:
            d: DfuDevice = copy.copy(d)
            d.__class__ = DfuDevice
            d.dfu_init()

            yield d

    if dev is None:
        return dev
    elif isinstance(dev, usb.core.Device):
        dev: DfuDevice = copy.copy(dev)
        dev.__class__ = DfuDevice
        dev.dfu_init()
        return dev
    elif isinstance(dev, Generator):
        return device_iter()


class DfuDevice(usb.core.Device):

    def __init__(self, dev, backend, dfu_timeout=None, num_connect_attempts=5):
        super(DfuDevice, self).__init__(dev, backend)
        self.dfu_init(dfu_timeout, num_connect_attempts)

    def dfu_init(self, dfu_timeout=None, num_connect_attempts=5):
        self.dfu_interface: usb.core.Interface = None
        self.dfu_descriptor: dict = None

        self.num_connect_attempts = num_connect_attempts

        dfu.dfu_init(dfu_timeout if dfu_timeout else 5000)
        dfu.dfu_debug(logging.INFO)

    @property
    def dfu_intf(self) -> [int, None]:
        if self.dfu_interface is not None:
            return self.dfu_interface.bInterfaceNumber
        return None

    def get_dfu_descriptor(self, interface: usb.core.Interface):
        try:
            extra = interface.extra_descriptors
            return USB_DFU_FUNC_DESCRIPTOR.parse(bytes(extra))
        except Exception as exc:
            logger.warning(
                f'DFU descriptor not found on interface {interface.bInterfaceNumber}: {self._str()}'
            )
            return None

    def get_dfu_interface(self):
        cfg: usb.core.Configuration = self.get_active_configuration()
        for intf in cfg.interfaces():
            if intf.bInterfaceClass != 0xfe or intf.bInterfaceSubClass != 1:
                continue

            dfu_desc = self.get_dfu_descriptor(intf)
            if dfu_desc:
                self.dfu_interface = intf
                self.dfu_descriptor = dfu_desc
                break

        if not self.dfu_interface:
            logger.error(f'No DFU interface found: {self._str()}')

    def get_status(self) -> (int, dict):
        _, status = dfu.dfu_get_status(self, self.dfu_intf)
        sleep(status.bwPollTimeout)
        sleep(0.5)
        return _, status

    def is_connect_valid(self):
        _, status = self.get_status()
        while status.bState != dfu.DFUState.DFU_IDLE:

            if status.bState in [dfu.DFUState.APP_IDLE, dfu.DFUState.APP_DETACH]:
                return False
            elif status.bState == dfu.DFUState.DFU_ERROR:
                if dfu.dfu_clear_status(self, self.dfu_intf) < 0:
                    return False
                _, status = self.get_status()
            elif status.bState in [dfu.DFUState.DFU_DOWNLOAD_IDLE, dfu.DFUState.DFU_UPLOAD_IDLE]:
                if dfu.dfu_abort(self, self.dfu_intf) < 0:
                    return False
                _, status = self.get_status()
            else:
                break

        if status.bStatus != dfu.DFUStatus.OK:
            if dfu.dfu_clear_status(self, self.dfu_intf) < 0:
                return False
            _, status = self.get_status()
            if _ < 0:
                return False
            if status.bStatus != dfu.DFUStatus.OK:
                return False
            sleep(status.bwPollTimeout)

        return True

    @property
    def usb_port(self):
        port = self.port_numbers
        enc_address = ":".join(f"{num:02X}" for num in port[:6]) + ":00" * (6 - len(port))
        return enc_address

    def dfu_detach(self) -> int:
        detach_timeout = self.dfu_descriptor.wDetachTimeOut / 10000
        detach_timeout = math.ceil(detach_timeout)
        dfu.dfu_detach(self, self.dfu_intf, 1000)
        sleep(1)
        return detach_timeout

    def connect(self, hold_port=True):
        if self.num_connect_attempts > 0:
            self.num_connect_attempts -= 1
            self.get_dfu_interface()
            if not self.dfu_interface:
                raise IOError(f'No DFU interface found: {self._str()}')

            if not self.is_connect_valid():
                detach_timeout = self.dfu_detach()
                self.reconnect(detach_timeout, hold_port)
        else:
            raise ConnectionError(f"Can't connect device: {self._str()}")

    def reconnect(self, count: int = 10, hold_port: bool = True):

        def reattach_device_handle() -> DfuDevice:
            if not hold_port:
                return find(idVendor=self.idVendor, idProduct=self.idProduct)

            devices = find(find_all=True, idVendor=self.idVendor, idProduct=self.idProduct)
            detached = tuple(filter(lambda d: d if d.port_numbers == self.port_numbers else None, devices))
            if len(detached) != 1:
                return None

            return detached[0]

        countdown = count
        dev_handle = None
        print('waiting', end='')
        while countdown > 0 and dev_handle is None:
            dev_handle: DfuDevice = reattach_device_handle()
            countdown -= 1
            sleep(1)
            print('.', end='')
        print()

        if dev_handle is None:
            raise ConnectionResetError(f"Can't reconnect device: {self._str()}")

        self.__dict__.update(dev_handle.__dict__)
        self.connect()

    def disconnect(self):
        usb.util.release_interface(self, self.dfu_intf)
        usb.util.dispose_resources(self)

    def do_upload(self, offset: int, length: int, page_size: int = 2048, callback=None):
        USB_PAGE = page_size

        total: int = length
        start_page: int = int(offset / USB_PAGE)
        page = start_page
        ret = bytes()

        upload_task = _progress_bar.add_task(
            '[magenta1]Starting upload',
            total=total
        )

        _progress_bar.callback = callback
        _progress_bar.start()

        try:

            while True:

                rc = dfu.dfu_upload(self, self.dfu_intf, page, USB_PAGE),

                if len(rc[0]) < 0:
                    ret = rc
                    break

                _progress_bar.update(upload_task, advance=USB_PAGE, description='[magenta1]Uploading...')

                ret += rc[0]

                if len(rc[0]) < USB_PAGE or (len(ret) >= total >= 0):
                    break
                page += 1

        except usb.core.USBTimeoutError:
            pass

        dfu.dfu_upload(self, self.dfu_intf, page, 0),

        _progress_bar.update(upload_task, advance=0, description='[yellow4]Upload finished!')
        _progress_bar.stop()
        _progress_bar.remove_task(upload_task)

        return ret

    def do_download(self):
        ...


dfudev: DfuDevice = find(idVendor=0x1FC9, idProduct=0x000C)
# dfudev: DfuDevice = find(idVendor=0x1FC9, idProduct=0x1002)

devs = find(find_all=True, idVendor=0x1FC9, idProduct=0x000C)
for dfudev in devs:

    if dfudev is not None:
        dfudev.connect()
        print(dfudev.usb_port)
        dfudev.disconnect()


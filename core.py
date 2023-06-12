import asyncio
import copy
import logging
import math
from time import sleep
from typing import Generator

import construct
import libusb_package
import usb.core
from rich import progress
from rich.console import Console
from rich.table import Table
from usb.backend import libusb1

from progress import DfuProgress
from pydfuutil import dfu
from pydfuutil.usb_dfu import USB_DFU_FUNC_DESCRIPTOR

# setting global params

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DFU_PROGRESS = DfuProgress(
    progress.TextColumn("[progress.description]{task.description}"),
    progress.BarColumn(10),
    progress.TaskProgressColumn(),
    progress.TimeRemainingColumn(),
    progress.DownloadColumn(),
    progress.TransferSpeedColumn(),
)

_task_desc = '[{color}]{port} {desc}'

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
            logger.warning(exc)
            raise ConnectionRefusedError(
                f'DFU descriptor not found on interface {interface.bInterfaceNumber}: {self._str()}'
            )

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
            raise ConnectionRefusedError(f'No DFU interface found: {self._str()}')

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

        upload_task = DFU_PROGRESS.add_task(
            _task_desc.format(color='magenta1', port=self.usb_port, desc='Starting upload'),
            total=total
        )

        DFU_PROGRESS.callback = callback

        try:

            while True:

                rc = dfu.dfu_upload(self, self.dfu_intf, page, USB_PAGE),
                page += 1

                if len(rc[0]) < 0:
                    ret = rc
                    break

                DFU_PROGRESS.update(
                    upload_task, advance=USB_PAGE,
                    # description='[magenta1]Uploading...'
                    description=_task_desc.format(
                        color='magenta1',
                        port=self.usb_port,
                        desc='Uploading...'
                    )
                )

                ret += rc[0]

                if len(rc[0]) < USB_PAGE or (len(ret) >= total >= 0):
                    break

        except usb.core.USBTimeoutError:
            pass

        dfu.dfu_upload(self, self.dfu_intf, page, 0),

        DFU_PROGRESS.update(
            upload_task, advance=0,
            description=_task_desc.format(
                color='yellow4', port=self.usb_port, desc='Upload finished!'
            )
        )
        # DFU_PROGRESS.stop()
        DFU_PROGRESS.remove_task(upload_task)

        return ret

    def do_download(self, offset: int, data: bytes, page_size: int = 2048, callback=None):

        total: int = len(data)
        start_page: int = int(offset / page_size)
        page = start_page
        ret = 0

        download_task = DFU_PROGRESS.add_task(
            _task_desc.format(color='magenta1', port=self.usb_port, desc='Starting download'),
            total=total
        )

        DFU_PROGRESS.callback = callback

        part_num = 0

        try:

            while True:

                part = data[part_num * page_size:part_num * page_size + page_size]

                rc = dfu.dfu_download(self, self.dfu_intf, page, part)
                page += 1
                part_num += 1

                if rc < 0:
                    ret = rc
                    break

                DFU_PROGRESS.update(
                    download_task, advance=page_size,
                    # description='[magenta1]Uploading...'
                    description=_task_desc.format(
                        color='magenta1',
                        port=self.usb_port,
                        desc='Downloading...'
                    )
                )

                ret += rc

                if rc < page_size or ret >= total >= 0:
                    break

        except usb.core.USBTimeoutError:
            pass

        dfu.dfu_upload(self, self.dfu_intf, page, 0),

        DFU_PROGRESS.update(
            download_task, advance=0,
            description=_task_desc.format(
                color='yellow4', port=self.usb_port, desc='Download finished!'
            )
        )

        DFU_PROGRESS.remove_task(download_task)

        return ret


if __name__ == '__main__':

    import threading

    DFU_PROGRESS.start()

    offset = 532480
    start = int((offset + 4096) / 2048)
    data = bytes(2048)

    # Create a console object
    console = Console()


    def table_changed(table_data):
        # Create a new table
        table = Table(title="Devices")

        table.add_column("#", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")

        # Add rows to the table with updated progress values
        for i, item in enumerate(table_data):
            table.add_row(str(i), *item)

        # Print the updated table
        console.clear()
        console.print(table)


    table_data = [0]
    try:
        while True:
            # Clear the console

            # devs = find(find_all=True)
            devs = usb.core.show_devices().split('\n')
            dfudevs = filter(lambda d: d.find('1fc9:000c') >= 0, devs)

            new_table_data = []

            # print(dfudevs)
            for dev in dfudevs:
                new_table_data.append((dev.split(',')[0], "Found"))

            if table_data != new_table_data:
                table_data = new_table_data
                table_changed(table_data)

            # Delay for a certain period before the next update
            sleep(2)
    except KeyboardInterrupt:
        pass


    async def read_dev(dfudev):
        try:

            result = dfudev.do_upload(offset=offset + 4096, length=2048 * 128, page_size=2048)
            print(f'{dfudev.usb_port} {result[:5]}, {len(result)}')
            dfudev.disconnect()
            return result
        except Exception as exc:
            logger.warning(exc)
            # pass

    async def write_dev(dfudev, data):
        try:

            result = dfudev.do_download(offset=offset + 4096, data=data[:2048], page_size=2048)
            results.append(result)

            dfudev.disconnect()
            return result
        except Exception as exc:
            logger.warning(exc)


    async def detach_dev(dfudev):
        try:
            dfudev.connect()
            logger.info(f'Connected: {dfudev.usb_port}')
            dfudev.disconnect()
            return dfudev
        except Exception as exc:
            logger.warning(exc)


    devs = list(find(find_all=True))

    loop = asyncio.get_event_loop()


    tasks = []
    for dfudev in devs:
        if dfudev is not None:
            tasks.append(detach_dev(dfudev))

    results = loop.run_until_complete(asyncio.gather(*tasks))
    results = [i for i in results if i is not None]

    table_data = []
    for dev in results:
        _, status = dev.get_status()
        table_data.append((dev.usb_port, dfu.dfu_state_to_string(status.bState)))

    table_changed(table_data)

    tasks = []
    for dfudev in results:
        if dfudev is not None:
            tasks.append(read_dev(dfudev))

    results_data = loop.run_until_complete(asyncio.gather(*tasks))

    table_data = []
    for dev in results:
        _, status = dev.get_status()
        table_data.append((dev.usb_port, dfu.dfu_state_to_string(status.bState)))
    table_changed(table_data)


    tasks = []
    for i, dfudev in enumerate(results):
        if dfudev is not None:

            data = bytearray(results_data[i])
            data[:8] = f'AAAAAAAA'.encode()
            task = write_dev(dfudev, data)
            tasks.append(task)
    results_data1 = loop.run_until_complete(asyncio.gather(*tasks))

    # print(results_data1)

    # # dfu_file = input("path to dfu:")

    DFU_PROGRESS.stop()


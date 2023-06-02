from enum import IntEnum

import usb.util
import usb.core
from construct import *


# dfu.h
class DFUStates(IntEnum):
    STATE_APP_IDLE = 0x00
    STATE_APP_DETACH = 0x01
    STATE_DFU_IDLE = 0x02
    STATE_DFU_DOWNLOAD_SYNC = 0x03
    STATE_DFU_DOWNLOAD_BUSY = 0x04
    STATE_DFU_DOWNLOAD_IDLE = 0x05
    STATE_DFU_MANIFEST_SYNC = 0x06
    STATE_DFU_MANIFEST = 0x07
    STATE_DFU_MANIFEST_WAIT_RESET = 0x08
    STATE_DFU_UPLOAD_IDLE = 0x09
    STATE_DFU_ERROR = 0x0a


class DFUStatus(IntEnum):
    DFU_STATUS_OK = 0x00
    DFU_STATUS_ERROR_TARGET = 0x01
    DFU_STATUS_ERROR_FILE = 0x02
    DFU_STATUS_ERROR_WRITE = 0x03
    DFU_STATUS_ERROR_ERASE = 0x04
    DFU_STATUS_ERROR_CHECK_ERASED = 0x05
    DFU_STATUS_ERROR_PROG = 0x06
    DFU_STATUS_ERROR_VERIFY = 0x07
    DFU_STATUS_ERROR_ADDRESS = 0x08
    DFU_STATUS_ERROR_NOTDONE = 0x09
    DFU_STATUS_ERROR_FIRMWARE = 0x0a
    DFU_STATUS_ERROR_VENDOR = 0x0b
    DFU_STATUS_ERROR_USBR = 0x0c
    DFU_STATUS_ERROR_POR = 0x0d
    DFU_STATUS_ERROR_UNKNOWN = 0x0e
    DFU_STATUS_ERROR_STALLEDPKT = 0x0f


class DFUCommands(IntEnum):
    DFU_DETACH = 0
    DFU_DNLOAD = 1
    DFU_UPLOAD = 2
    DFU_GETSTATUS = 3
    DFU_CLRSTATUS = 4
    DFU_GETSTATE = 5
    DFU_ABORT = 6


# /* DFU interface */
DFU_IFF_DFU = 0x0001


# /* DFU Mode, (not Runtime) */
class DFUMode(IntEnum):
    DFU_IFF_VENDOR = 0x0100
    DFU_IFF_PRODUCT = 0x0200
    DFU_IFF_CONFIG = 0x0400
    DFU_IFF_IFACE = 0x0800
    DFU_IFF_ALT = 0x1000
    DFU_IFF_DEVNUM = 0x2000
    DFU_IFF_PATH = 0x4000


dfu_status = Struct(
    'bStatus' / Byte,
    'bwPollTimeout' / Int16ul,
    'bState' / Byte,
    'iString' / Byte
)

# Todo: dataclass typed dictor Struct
dfu_if = Struct(
    'vendor' / Int16ul,
    'product' / Int16ul,
    'bcdDevice' / Int16ul,
    'configuration' / Int8ul,
    'interface' / Int8ul,
    'altsetting' / Int8ul,
    'alt_name' / CString('utf-8'),
    'bus' / Int16ul,
    'devnum' / Int8ul,
    'path' / CString('utf-8'),
    'flags' / Int16ul,
    'count' / Int16ul,
    # 'dev' / libusb_device,
    # 'dev_handle' / libusb_device_handle,
)


def dfu_init(timeout: int) -> None:
    pass


def dfu_debug(level: int) -> None:
    pass


def dfu_detach(device: usb.core.Device, interface: int, timeout: int) -> int:
    return device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_DETACH,
        wValue=timeout,
        wIndex=interface,
        data_or_wLength=None,
        # wLength=length,
        timeout=dfu_timeout,
    )


def dfu_download(device: 'Device', interface: int, length: int, data: bytes) -> int:
    pass


def dfu_upload(device: usb.core.Device, interface: int, transaction: int, data: bytes) -> int:
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

    return device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_UPLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data,
        # wLength=length,
        timeout=dfu_timeout,
    )


# TODO: int out
def dfu_get_status(device: usb.core.Device, interface: int) -> int:
    buffer = bytes(6)

    status = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_GETSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=buffer,
        # wLength=length,
        timeout=dfu_timeout,
    )
    # print('result', status)
    buffer = status.tobytes()
    # print('bStatus', buffer[0], DFUStatus(buffer[0]).name)
    # print('bwPollTimeout', ((0xff & buffer[3]) << 16) | ((0xff & buffer[2]) << 8) | (0xff & buffer[1]))
    #
    # print('bState', buffer[4], DFUStates(buffer[4]).name)
    # print('iString', buffer[5])
    print(dfu_status.parse(buffer), DFUStatus(buffer[0]).name, DFUStates(buffer[4]).name)
    return dfu_status.parse(buffer)


def dfu_clear_status(device: usb.core.Device, interface: int) -> int:
    status = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_CLRSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        # wLength=length,
        timeout=dfu_timeout,
    )
    return status.tobytes()


def dfu_get_state(device: 'Device', interface: int) -> int:
    pass


def dfu_abort(device: 'Device', interface: int) -> int:
    pass


def dfu_state_to_string(state: int) -> str:
    pass


def dfu_status_to_string(status: int) -> str:
    pass


debug: int = 0

# dfu.c

INVALID_DFU_TIMEOUT = -1

dfu_timeout: int = INVALID_DFU_TIMEOUT
transaction: int = 0

dfu_debug_level: int = 0

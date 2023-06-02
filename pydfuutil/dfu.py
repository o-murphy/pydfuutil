from enum import IntEnum

import usb.core
import usb.util
from construct import *


# dfu.h
class DFUState(IntEnum):
    APP_IDLE = 0x00
    APP_DETACH = 0x01
    DFU_IDLE = 0x02
    DFU_DOWNLOAD_SYNC = 0x03
    DFU_DOWNLOAD_BUSY = 0x04
    DFU_DOWNLOAD_IDLE = 0x05
    DFU_MANIFEST_SYNC = 0x06
    DFU_MANIFEST = 0x07
    DFU_MANIFEST_WAIT_RESET = 0x08
    DFU_UPLOAD_IDLE = 0x09
    DFU_ERROR = 0x0a


dfu_states_names = {
    DFUState.APP_IDLE: 'appIDLE',
    DFUState.APP_DETACH: 'appDETACH',
    DFUState.DFU_IDLE: 'dfuIDLE',
    DFUState.DFU_DOWNLOAD_SYNC: 'dfuDNLOAD-SYNC',
    DFUState.DFU_DOWNLOAD_BUSY: 'dfuDNBUSY',
    DFUState.DFU_DOWNLOAD_IDLE: 'dfuDNLOAD-IDLE',
    DFUState.DFU_MANIFEST_SYNC: 'dfuMANIFEST-SYNC',
    DFUState.DFU_MANIFEST: 'dfuMANIFEST',
    DFUState.DFU_MANIFEST_WAIT_RESET: 'dfuMANIFEST-WAIT-RESET',
    DFUState.DFU_UPLOAD_IDLE: 'dfuUPLOAD-IDLE',
    DFUState.DFU_ERROR: 'dfuERROR',
}


class DFUStatus(IntEnum):
    OK = 0x00
    ERROR_TARGET = 0x01
    ERROR_FILE = 0x02
    ERROR_WRITE = 0x03
    ERROR_ERASE = 0x04
    ERROR_CHECK_ERASED = 0x05
    ERROR_PROG = 0x06
    ERROR_VERIFY = 0x07
    ERROR_ADDRESS = 0x08
    ERROR_NOTDONE = 0x09
    ERROR_FIRMWARE = 0x0a
    ERROR_VENDOR = 0x0b
    ERROR_USBR = 0x0c
    ERROR_POR = 0x0d
    ERROR_UNKNOWN = 0x0e
    ERROR_STALLEDPKT = 0x0f


dfu_status_names = {
    DFUStatus.OK: "No error condition is present",
    DFUStatus.ERROR_TARGET: "File is not targeted for use by this device",
    DFUStatus.ERROR_FILE: "File is for this device but fails some vendor-specific test",
    DFUStatus.ERROR_WRITE: "Device is unable to write memory",
    DFUStatus.ERROR_ERASE: "Memory erase function failed",
    DFUStatus.ERROR_CHECK_ERASED: "Memory erase check failed",
    DFUStatus.ERROR_PROG: "Program memory function failed",
    DFUStatus.ERROR_VERIFY: "Programmed memory failed verification",
    DFUStatus.ERROR_ADDRESS: "Cannot program memory due to received address that is out of range",
    DFUStatus.ERROR_NOTDONE: "Received DFU_DNLOAD with wLength = 0, but device does not think that it has all data yet",
    DFUStatus.ERROR_FIRMWARE: "Device's firmware is corrupt. It cannot return to run-time (non-DFU) operations",
    DFUStatus.ERROR_VENDOR: "iString indicates a vendor specific error",
    DFUStatus.ERROR_USBR: "Device detected unexpected USB reset signalling",
    DFUStatus.ERROR_POR: "Device detected unexpected power on reset",
    DFUStatus.ERROR_UNKNOWN: "Something went wrong, but the device does not know what it was",
    DFUStatus.ERROR_STALLEDPKT: "Device stalled an unexpected request"

}


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
    'bwPollTimeout' / BytesInteger(3),
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
    raise NotImplementedError()


def dfu_debug(level: int) -> None:
    raise NotImplementedError()


def dfu_detach(device: usb.core.Device, interface: int, timeout: int) -> bytes:
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_DETACH,
        wValue=timeout,
        wIndex=interface,
        data_or_wLength=None,
        timeout=dfu_timeout,
    )
    return result.tobytes()


def dfu_download(device: usb.core.Device, interface: int, transaction: int, data: bytes) -> bytes:
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_DNLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data,
        timeout=dfu_timeout,
    )
    return result.tobytes()


def dfu_upload(device: usb.core.Device, interface: int, transaction: int, data: bytes) -> bytes:
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_UPLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data,
        timeout=dfu_timeout,
    )
    return result.tobytes()


# TODO: int out
def dfu_get_status(device: usb.core.Device, interface: int) -> (int, dict):
    status = Container(
        bStatus=DFUStatus.ERROR_UNKNOWN,
        bwPollTimeout=0,
        bState=DFUState.DFU_ERROR,
        iString=0
    )

    length = 6
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_GETSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=length,
        timeout=dfu_timeout,
    )
    if len(result) == 6:
        con = dfu_status.parse(result.tobytes())
        con.pop('_io')
        status.update(con)
    return int.from_bytes(result.tobytes(), byteorder='little'), status


def dfu_clear_status(device: usb.core.Device, interface: int) -> int:
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_CLRSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=dfu_timeout,
    )
    return int.from_bytes(result.tobytes(), byteorder='little')


def dfu_get_state(device: usb.core.Device, interface: int) -> int:
    length = 1
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_GETSTATE,
        wValue=0,
        wIndex=interface,
        data_or_wLength=length,
        timeout=dfu_timeout,
    )

    if result.tobytes()[0] < 1:
        return -1
    return result.tobytes()[0]


def dfu_abort(device: usb.core.Device, interface: int) -> int:
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_ABORT,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=dfu_timeout,
    )

    return int.from_bytes(result.tobytes(), byteorder='little')


def dfu_state_to_string(state: int) -> [str, None]:
    try:
        return dfu_states_names[DFUState(state)]
    except (ValueError, KeyError):
        return None


def dfu_status_to_string(status: int) -> [str, None]:
    try:
        return dfu_status_names[DFUStatus(status)]
    except (ValueError, KeyError):
        return None


debug: int = 0

# dfu.c

INVALID_DFU_TIMEOUT = -1

dfu_timeout: int = INVALID_DFU_TIMEOUT
transaction: int = 0

dfu_debug_level: int = 0

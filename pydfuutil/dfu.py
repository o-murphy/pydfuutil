"""
low-level DFU message sending routines (part of dfu-programmer).
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import inspect
import logging
from dataclasses import dataclass
from enum import IntEnum

import usb.util
from construct import Byte, Struct, BytesInteger, Container

logging.basicConfig(level=logging.DEBUG,
                    # filemode='w',
                    # filename='dfu.log',
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DFUState(IntEnum):
    """Dfu states"""
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


_DFU_STATES_NAMES = {
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
    """Dfu statuses"""
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


_DFU_STATUS_NAMES = {
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
    """Dfu commands"""
    DFU_DETACH = 0
    DFU_DNLOAD = 1
    DFU_UPLOAD = 2
    DFU_GETSTATUS = 3
    DFU_CLRSTATUS = 4
    DFU_GETSTATE = 5
    DFU_ABORT = 6


# /* DFU interface */
class DFUMode(IntEnum):
    """Dfu modes"""
    DFU_IFF_DFU = 0x0001  # /* DFU Mode, (not Runtime) */
    DFU_IFF_VENDOR = 0x0100
    DFU_IFF_PRODUCT = 0x0200
    DFU_IFF_CONFIG = 0x0400
    DFU_IFF_IFACE = 0x0800
    DFU_IFF_ALT = 0x1000
    DFU_IFF_DEVNUM = 0x2000
    DFU_IFF_PATH = 0x4000


_DFU_STATUS = Struct(
    bStatus=Byte,
    bwPollTimeout=BytesInteger(3),
    bState=Byte,
    iString=Byte
)


@dataclass
class DFU_IF:
    """DFU_IF structure implementation"""

    __slots__ = [
        'vendor', 'product', 'bcdDevice',
        'configuration', 'interface',
        'altsetting', 'alt_name',
        'bus', 'devnum',
        'path', 'flags', 'count',
        'dev',
        # 'dev_handle'
    ]

    def __init__(self, vendor: int, product: int, bcdDevice: int,
                 configuration: int, interface: int,
                 altsetting: int, alt_name: str,
                 bus: int, devnum: int,
                 path: [str, int], flags: int, count: int,
                 dev: usb.core.Device,
                 # dev_handle: usb.core.Device
                 ):
        self.vendor = vendor
        self.product = product
        self.bcdDevice = bcdDevice
        self.configuration = configuration
        self.interface = interface
        self.altsetting = altsetting
        self.alt_name = alt_name  # or Bytes() pointer
        self.bus = bus
        self.devnum = devnum
        self.path = path  # or Bytes() pointer
        self.flags = flags
        self.count = count
        self.dev = dev


def dfu_init(timeout: int) -> None:
    """
    Initiate dfu_util library with specified commands timeout
    :param timeout in milliseconds
    :return: None
    """

    global DFU_TIMEOUT

    if timeout > 0:
        DFU_TIMEOUT = timeout
    else:
        if 0 != DFU_DEBUG_LEVEL:
            raise ValueError(f"dfu_init: Invalid timeout value {timeout}")


def dfu_verify_init() -> int:  # NOTE: (function: typing.Callable) not needed cause python can get it from stack
    """
    Verifies setted DFU_TIMEOUT and DFU_DEBUG_LEVEL
    :raise ValueError with caller function name
    :return: 0
    """
    caller = inspect.stack()[0][3]
    if INVALID_DFU_TIMEOUT == DFU_TIMEOUT:
        if 0 != DFU_DEBUG_LEVEL:
            raise ValueError(f'"{caller}": dfu system not property initialized.')
    return 0


def dfu_debug(level: int) -> None:
    """
    NOTE: Maybe not needed cause python can define globals after
    :param level: logging.level
    """

    global DFU_DEBUG_LEVEL
    DFU_DEBUG_LEVEL = level
    logger.setLevel(level)


def dfu_detach(device: usb.core.Device, interface: int, timeout: int) -> bytes:
    """

     *  DFU_DETACH Request (DFU Spec 1.0, Section 5.1)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  timeout   - the timeout in ms the USB device should wait for a pending
     *              USB reset before giving up and terminating the operation
     *
     *  returns 0 or < 0 on error

    Sends to device command to switch it to DFU mode
    u have to free device and handle it again
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :param timeout: timeout to dfu detach
    :return: returns error code
    """
    dfu_verify_init()
    logger.debug('DFU_DETACH...')
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_DETACH,
        wValue=timeout,
        wIndex=interface,
        data_or_wLength=None,
        timeout=DFU_TIMEOUT,
    )
    logger.debug(f'DFU_DETACH {result >= 0}')
    return result


def dfu_download(device: usb.core.Device, interface: int, transaction: int, data_or_length: [bytes, int]) -> int:
    """
     *  DFU_DNLOAD Request (DFU Spec 1.0, Section 6.1.1)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  length    - the total number of bytes to transfer to the USB
     *              device - must be less than wTransferSize
     *  data      - the data to transfer
     *
     *  returns the number of bytes written or < 0 on error

    Download data to special page of DFU device
    :param device: usb.core.Device
    :param interface: usb.core.interface.bInterfaceNumber
    :param transaction: start page int(total_data_size/xfer_size)
    :param data_or_length: page size bytes(xfer_size) or xfer_size
    :return: downloaded data or error code in bytes
    """
    dfu_verify_init()
    logger.debug('DFU_DOWNLOAD...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_DNLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data_or_length,
        timeout=DFU_TIMEOUT,
    )

    logger.debug(f'DFU_DOWNLOAD {result >= 0}')
    return result


def dfu_upload(device: usb.core.Device, interface: int, transaction: int, data_or_length: [bytes, int]) -> bytes:
    """
     *  DFU_UPLOAD Request (DFU Spec 1.0, Section 6.2)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  length    - the maximum number of bytes to receive from the USB
     *              device - must be less than wTransferSize
     *  data      - the buffer to put the received data in
     *
     *  returns the number of bytes received or < 0 on error

    Uploads data from special page of DFU device
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :param transaction: start page int(total_data_size/xfer_size)
    :param data_or_length: page size bytes(xfer_size) or xfer_size
    :return: uploaded data or error code in bytes
    """
    dfu_verify_init()
    logger.debug('DFU_UPLOAD...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_UPLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data_or_length,
        timeout=DFU_TIMEOUT,
    )

    logger.debug(f'DFU_UPLOAD {len(result) >= 0}')

    return result.tobytes()


def dfu_get_status(device: usb.core.Device, interface: int) -> (int, dict):
    """
     *  DFU_GETSTATUS Request (DFU Spec 1.0, Section 6.1.2)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  status    - the data structure to be populated with the results
     *
     *  return the number of bytes read in or < 0 on an error

    Returns DFU interface status
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :return: error code and _DFU_STATUS [Container, dict] object
    """
    dfu_verify_init()
    logger.debug('DFU_GET_STATUS...')

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
        timeout=DFU_TIMEOUT,
    )

    if len(result) == 6:
        con = _DFU_STATUS.parse(result.tobytes())
        con.pop('_io')
        status.update(con)
    logger.debug(f'DFU_GET_STATUS {len(result) == 6}')
    logger.debug(f'CURRENT STATE {dfu_state_to_string(status.bState)}')
    return int.from_bytes(result.tobytes(), byteorder='little'), status


def dfu_clear_status(device: usb.core.Device, interface: int) -> int:
    """
     *  DFU_CLRSTATUS Request (DFU Spec 1.0, Section 6.1.3)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *
     *  return 0 or < 0 on an error

    Clears DFU interface status
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :return: error code
    """
    dfu_verify_init()
    logger.debug('DFU_CLEAR_STATUS...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_CLRSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=DFU_TIMEOUT,
    )
    logger.debug(f'DFU_CLEAR_STATUS {result >= 0}')

    return result


def dfu_get_state(device: usb.core.Device, interface: int) -> int:
    """
     *  DFU_GETSTATE Request (DFU Spec 1.0, Section 6.1.5)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  length    - the maximum number of bytes to receive from the USB
     *              device - must be less than wTransferSize
     *  data      - the buffer to put the received data in
     *
     *  returns the state or < 0 on error

    Returns DFU interface state
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :return: dfu state or error code
    """
    dfu_verify_init()

    length = 1
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_GETSTATE,
        wValue=0,
        wIndex=interface,
        data_or_wLength=length,
        timeout=DFU_TIMEOUT,
    )

    if result.tobytes()[0] < 1:
        return -1
    return result.tobytes()[0]


def dfu_abort(device: usb.core.Device, interface: int) -> int:
    """
     *  DFU_ABORT Request (DFU Spec 1.0, Section 6.1.4)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *
     *  returns 0 or < 0 on an error

    Aborts DFU command
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :return: error code
    """
    dfu_verify_init()
    logger.debug('DFU_ABORT...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=DFUCommands.DFU_ABORT,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=DFU_TIMEOUT,
    )

    logger.debug(f'DFU_ABORT {result >= 0}')

    return result


def dfu_state_to_string(state: int) -> [str, None]:
    """
    :param state:
    :return: State name by DFUState Enum
    """
    try:
        return _DFU_STATES_NAMES[DFUState(state)]
    except (ValueError, KeyError):
        return None


def dfu_status_to_string(status: int) -> [str, None]:
    """
    :param status:
    :return: State name by DFUStatus Enum
    """
    try:
        return _DFU_STATUS_NAMES[DFUStatus(status)]
    except (ValueError, KeyError):
        return None


# global definitions
DEBUG: int = 0

INVALID_DFU_TIMEOUT = -1

DFU_TIMEOUT: int = INVALID_DFU_TIMEOUT
DFU_TRANSACTION: int = 0

DFU_DEBUG_LEVEL: int = 0

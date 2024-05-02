"""
low-level DFU message sending routines (part of dfu-programmer).
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import inspect
import logging
from dataclasses import dataclass
from enum import IntEnum, IntFlag

import usb.util

from pydfuutil.logger import logger


_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])
_logger.setLevel(logging.DEBUG)


class State(IntEnum):
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

    UNKNOWN_ERROR = -1

    def to_string(self):
        """
        :return: State.self name by State Enum
        """
        return state_to_string(self)


_STATES_NAMES = {
    State.APP_IDLE: 'appIDLE',
    State.APP_DETACH: 'appDETACH',
    State.DFU_IDLE: 'dfuIDLE',
    State.DFU_DOWNLOAD_SYNC: 'dfuDNLOAD-SYNC',
    State.DFU_DOWNLOAD_BUSY: 'dfuDNBUSY',
    State.DFU_DOWNLOAD_IDLE: 'dfuDNLOAD-IDLE',
    State.DFU_MANIFEST_SYNC: 'dfuMANIFEST-SYNC',
    State.DFU_MANIFEST: 'dfuMANIFEST',
    State.DFU_MANIFEST_WAIT_RESET: 'dfuMANIFEST-WAIT-RESET',
    State.DFU_UPLOAD_IDLE: 'dfuUPLOAD-IDLE',
    State.DFU_ERROR: 'dfuERROR',
}


class Status(IntEnum):
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

    def to_string(self):
        """
        :return: Status.self name by Status Enum
        """
        return status_to_string(self)


_DFU_STATUS_NAMES = {
    Status.OK: "No error condition is present",
    Status.ERROR_TARGET: "File is not targeted for use by this device",
    Status.ERROR_FILE: "File is for this device but fails some vendor-specific test",
    Status.ERROR_WRITE: "Device is unable to write memory",
    Status.ERROR_ERASE: "Memory erase function failed",
    Status.ERROR_CHECK_ERASED: "Memory erase check failed",
    Status.ERROR_PROG: "Program memory function failed",
    Status.ERROR_VERIFY: "Programmed memory failed verification",
    Status.ERROR_ADDRESS: "Cannot program memory due to received address that is out of range",
    Status.ERROR_NOTDONE: "Received DNLOAD with wLength = 0, "
                          "but device does not think that it has all data yet",
    Status.ERROR_FIRMWARE: "Device's firmware is corrupt. "
                           "It cannot return to run-time (non-DFU) operations",
    Status.ERROR_VENDOR: "iString indicates a vendor specific error",
    Status.ERROR_USBR: "Device detected unexpected USB reset signalling",
    Status.ERROR_POR: "Device detected unexpected power on reset",
    Status.ERROR_UNKNOWN: "Something went wrong, but the device does not know what it was",
    Status.ERROR_STALLEDPKT: "Device stalled an unexpected request"

}


class Command(IntEnum):
    """Dfu commands"""
    DETACH = 0
    DNLOAD = 1
    UPLOAD = 2
    GETSTATUS = 3
    CLRSTATUS = 4
    GETSTATE = 5
    ABORT = 6


# /* DFU interface */
class Mode(IntFlag):
    """Dfu modes"""
    IFF_DFU = 0x0001  # /* DFU Mode, (not Runtime) */
    IFF_VENDOR = 0x0100
    IFF_PRODUCT = 0x0200
    IFF_CONFIG = 0x0400
    IFF_IFACE = 0x0800
    IFF_ALT = 0x1000
    IFF_DEVNUM = 0x2000
    IFF_PATH = 0x4000


@dataclass(frozen=True)
class StatusRetVal:
    """
    Converts dfu_get_status result bytes to applicable dataclass
    """
    # pylint: disable=invalid-name
    bStatus: Status = Status.ERROR_UNKNOWN
    bwPollTimeout: int = 0
    bState: State = State.DFU_ERROR
    iString: int = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        """Creates StatusRetVal instance from bytes sequence"""
        if len(data) >= 6:
            bStatus = (Status(data[0])
                       if data[0] in Status.__members__.values()
                       else Status.ERROR_UNKNOWN)
            bwPollTimeout = int.from_bytes(data[1:4], 'little')
            bState = (State(data[4])
                      if data[0] in State.__members__.values()
                      else State.DFU_ERROR)
            iString = data[5]
            return cls(
                bStatus,
                bwPollTimeout,
                bState,
                iString
            )
        return cls()

    def __bytes__(self) -> bytes:
        return (
                bytes([self.bStatus.value])
                + self.bwPollTimeout.to_bytes(3, 'little')
                + bytes([self.bState.value, self.iString])
        )

    def __int__(self):
        return int.from_bytes(self, 'little')


@dataclass
class DfuIf:  # pylint: disable=too-many-instance-attributes

    """DFU Interface dataclass"""
    # pylint: disable=invalid-name

    vendor: int = None
    product: int = None
    bcdDevice: int = None
    configuration: int = None
    interface: int = None
    altsetting: int = None
    alt_name: str = None
    bus: int = None
    devnum: int = None
    path: [str, int] = None
    flags: [Mode, int] = None
    count: int = None
    dev: usb.core.Device = None

    @property
    def device_ids(self) -> dict:
        """Returns filter dict for usb.core.find() by VID:PID"""
        id_filter = {}
        if self.vendor:
            id_filter["idVendor"] = self.vendor
        if self.product:
            id_filter["idProduct"] = self.product
        return id_filter

    # The binds to direct dfu functions to get more pythonic
    # Use them better instead of direct

    def detach(self, timeout: int) -> bytes:
        """Binds self to dfu.detach()"""
        return detach(self.dev, self.interface, timeout)

    def download(self, transaction: int, data_or_length: [bytes, int]) -> int:
        """Binds self to dfu.download()"""
        return download(self.dev, self.interface, transaction, data_or_length)

    def upload(self, transaction: int, data_or_length: [bytes, int]) -> bytes:
        """Binds self to dfu.upload()"""
        return upload(self.dev, self.interface, transaction, data_or_length)

    def abort(self) -> int:
        """Binds self to dfu.abort()"""
        return abort(self.dev, self.interface)

    def get_status(self) -> StatusRetVal:
        """Binds self to dfu.get_status()"""
        return get_status(self.dev, self.interface)

    def get_state(self) -> State:
        """Binds self to dfu.get_state()"""
        return get_state(self.dev, self.interface)


def init(timeout: int) -> None:
    """
    Initiate dfu_util library with specified commands timeout
    :param timeout in milliseconds
    :return: None
    """

    # pylint: disable=global-statement
    global TIMEOUT

    if timeout > 0:
        TIMEOUT = timeout
    else:
        if 0 != DEBUG_LEVEL:
            raise ValueError(f"dfu_init: Invalid timeout value {timeout}")


def verify_init() -> int:
    """
    Verifies provided TIMEOUT and DEBUG_LEVEL
    NOTE: (function: typing.Callable) not needed cause python can get it from stack
    :raise ValueError with caller function name
    :return: 0
    """
    caller = inspect.stack()[0][3]
    if INVALID_DFU_TIMEOUT == TIMEOUT:
        if 0 != DEBUG_LEVEL:
            raise ValueError(f'"{caller}": dfu system not initialized properly.')
    return 0


def debug(level: int) -> None:
    """
    NOTE: Maybe not needed cause python can define globals after
    :param level: logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # pylint: disable=global-statement
    global DEBUG_LEVEL
    DEBUG_LEVEL = level
    _logger.setLevel(level)


def detach(device: usb.core.Device, interface: int, timeout: int) -> bytes:
    """

     *  DETACH Request (DFU Spec 1.0, Section 5.1)
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
    verify_init()
    _logger.debug('DETACH...')
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.DETACH,
        wValue=timeout,
        wIndex=interface,
        data_or_wLength=None,
        timeout=TIMEOUT,
    )
    _logger.debug(f'DETACH {result >= 0}')
    return result


def download(device: usb.core.Device,
             interface: int,
             transaction: int,
             data_or_length: [bytes, int]) -> int:
    """
     *  DNLOAD Request (DFU Spec 1.0, Section 6.1.1)
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
    verify_init()
    _logger.debug('DFU_DOWNLOAD...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.DNLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data_or_length,
        timeout=TIMEOUT,
    )

    _logger.debug(f'DFU_DOWNLOAD {result >= 0}')
    return result


def upload(device: usb.core.Device,
           interface: int,
           transaction: int,
           data_or_length: [bytes, int]) -> bytes:
    """
     *  UPLOAD Request (DFU Spec 1.0, Section 6.2)
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
    verify_init()
    _logger.debug('UPLOAD...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.UPLOAD,
        wValue=transaction,
        wIndex=interface,
        data_or_wLength=data_or_length,
        timeout=TIMEOUT,
    )

    _logger.debug(f'UPLOAD {len(result) >= 0}')

    return result.tobytes()


def get_status(device: usb.core.Device, interface: int) -> StatusRetVal:
    """
     *  GETSTATUS Request (DFU Spec 1.0, Section 6.1.2)
     *
     *  device    - the usb_dev_handle to communicate with
     *  interface - the interface to communicate with
     *  status    - the data structure to be populated with the results
     *
     *  return the number of bytes read in or < 0 on an error

    Returns DFU interface status
    :param device: usb.core.Device
    :param interface: usb.core.Interface.bInterfaceNumber
    :return: error code and _STATUS [Container, dict] object
    """
    verify_init()
    _logger.debug('DFU_GET_STATUS...')

    length = 6
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.GETSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=length,
        timeout=TIMEOUT,
    )

    if len(result) == length:
        status = StatusRetVal.from_bytes(result.tobytes())
        _logger.debug(f'GET_STATUS {len(result) == 6}')
        _logger.debug(f'CURRENT STATE {status.bState.to_string()}')
        return status
    return StatusRetVal.from_bytes(result)


def clear_status(device: usb.core.Device, interface: int) -> int:
    """
     *  CLRSTATUS Request (DFU Spec 1.0, Section 6.1.3)
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
    verify_init()
    _logger.debug('CLEAR_STATUS...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.CLRSTATUS,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=TIMEOUT,
    )
    _logger.debug(f'CLEAR_STATUS {result >= 0}')

    return result


def get_state(device: usb.core.Device, interface: int) -> [State, int]:
    """
     *  GETSTATE Request (DFU Spec 1.0, Section 6.1.5)
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
    verify_init()

    length = 1
    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_IN
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.GETSTATE,
        wValue=0,
        wIndex=interface,
        data_or_wLength=length,
        timeout=TIMEOUT,
    )
    value = result.tobytes()[0] < 1
    if value < 1:
        return State(-1)
    if value in State.__members__.values():
        value = State(value)
    return value


def abort(device: usb.core.Device, interface: int) -> int:
    """
     *  ABORT Request (DFU Spec 1.0, Section 6.1.4)
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
    verify_init()
    _logger.debug('ABORT...')

    result = device.ctrl_transfer(
        bmRequestType=usb.util.ENDPOINT_OUT
                      | usb.util.CTRL_TYPE_CLASS
                      | usb.util.CTRL_RECIPIENT_INTERFACE,
        bRequest=Command.ABORT,
        wValue=0,
        wIndex=interface,
        data_or_wLength=None,
        timeout=TIMEOUT,
    )

    _logger.debug(f'ABORT {result >= 0}')

    return result


def state_to_string(state: int) -> [str, None]:
    """
    :param state:
    :return: State name by State Enum
    """
    try:
        return _STATES_NAMES[State(state)]
    except (ValueError, KeyError):
        return None


def status_to_string(status: int) -> [str, None]:
    """
    :param status:
    :return: State name by Status Enum
    """
    try:
        return _DFU_STATUS_NAMES[Status(status)]
    except (ValueError, KeyError):
        return None


# global definitions
DEBUG: int = 0

INVALID_DFU_TIMEOUT = -1

TIMEOUT: int = INVALID_DFU_TIMEOUT
TRANSACTION: int = 0

DEBUG_LEVEL: int = 0

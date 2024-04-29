"""
low-level DFU message sending routines (part of dfu-programmer).
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
"""

import inspect
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag

import usb.util
from construct import Byte, Struct, BytesInteger, Container

from pydfuutil.logger import get_logger

logger = get_logger(__name__)


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


_STATUS = Struct(
    bStatus=Byte,
    bwPollTimeout=BytesInteger(3),
    bState=Byte,
    iString=Byte
)


@dataclass
class DfuIf:  # pylint: disable=too-many-instance-attributes

    """DfuIf structure implementation"""

    vendor: int = field(default=None, )
    product: int = field(default=None, )
    bcdDevice: int = field(default=0, )
    configuration: int = field(default=0, )
    interface: int = field(default=0, )
    altsetting: int = field(default=0, )
    alt_name: str = field(default="", )
    bus: int = field(default=0, )
    devnum: int = field(default=0, )
    path: [str, int] = field(default="", )
    flags: [Mode, int] = field(default=0, )
    count: int = field(default=0, )
    dev: usb.core.Device = field(default=None)

    @property
    def device_ids(self) -> dict:
        id_filter = {}
        if self.vendor:
            id_filter["idVendor"] = self.vendor
        if self.product:
            id_filter["idProduct"] = self.product
        return id_filter

    # __slots__ = (
    #     'vendor', 'product', 'bcdDevice',
    #     'configuration', 'interface',
    #     'altsetting', 'alt_name',
    #     'bus', 'devnum',
    #     'path', 'flags', 'count',
    #     'dev',
    # )

    # # pylint: disable=too-many-arguments, invalid-name
    # def __init__(self, vendor: int, product: int, bcdDevice: int,
    #              configuration: int, interface: int,
    #              altsetting: int, alt_name: str,
    #              bus: int, devnum: int,
    #              path: [str, int], flags: int, count: int,
    #              dev: usb.core.Device):
    #
    #     self.vendor = vendor
    #     self.product = product
    #     self.bcdDevice = bcdDevice
    #     self.configuration = configuration
    #     self.interface = interface
    #     self.altsetting = altsetting
    #     self.alt_name = alt_name  # or Bytes() pointer
    #     self.bus = bus
    #     self.devnum = devnum
    #     self.path = path  # or Bytes() pointer
    #     self.flags = flags
    #     self.count = count
    #     self.dev = dev


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
    Verifies setted TIMEOUT and DEBUG_LEVEL
    NOTE: (function: typing.Callable) not needed cause python can get it from stack
    :raise ValueError with caller function name
    :return: 0
    """
    caller = inspect.stack()[0][3]
    if INVALID_DFU_TIMEOUT == TIMEOUT:
        if 0 != DEBUG_LEVEL:
            raise ValueError(f'"{caller}": dfu system not property initialized.')
    return 0


def debug(level: int) -> None:
    """
    NOTE: Maybe not needed cause python can define globals after
    :param level: logging.level
    """

    # pylint: disable=global-statement
    global DEBUG_LEVEL
    DEBUG_LEVEL = level
    logger.setLevel(level)


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
    logger.debug('DETACH...')
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
    logger.debug(f'DETACH {result >= 0}')
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
    logger.debug('DFU_DOWNLOAD...')

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

    logger.debug(f'DFU_DOWNLOAD {result >= 0}')
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
    logger.debug('UPLOAD...')

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

    logger.debug(f'UPLOAD {len(result) >= 0}')

    return result.tobytes()


def get_status(device: usb.core.Device, interface: int) -> (int, dict):
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
    logger.debug('DFU_GET_STATUS...')

    status = Container(
        bStatus=Status.ERROR_UNKNOWN,
        bwPollTimeout=0,
        bState=State.DFU_ERROR,
        iString=0
    )

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

    if len(result) == 6:
        con = _STATUS.parse(result.tobytes())
        con.pop('_io')
        status.update(con)
    logger.debug(f'DFU_GET_STATUS {len(result) == 6}')
    logger.debug(f'CURRENT STATE {state_to_string(status.bState)}')
    return int.from_bytes(result.tobytes(), byteorder='little'), status


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
    logger.debug('DFU_CLEAR_STATUS...')

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
    logger.debug(f'DFU_CLEAR_STATUS {result >= 0}')

    return result


def get_state(device: usb.core.Device, interface: int) -> int:
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

    if result.tobytes()[0] < 1:
        return -1
    return result.tobytes()[0]


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
    logger.debug('ABORT...')

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

    logger.debug(f'ABORT {result >= 0}')

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

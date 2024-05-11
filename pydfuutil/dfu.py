"""
Low-level DFU communication routines (part of dfu-programmer).
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

# import inspect
import sys
from dataclasses import dataclass
from enum import IntEnum, IntFlag

import usb.util

from pydfuutil.dfuse_mem import MemSegment
from pydfuutil.logger import logger
from pydfuutil.portable import milli_sleep
from pydfuutil.usb_dfu import FuncDescriptor

_logger = logger.getChild(__name__.rsplit('.', maxsplit=1)[-1])


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
        return _state_to_string(self)


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
        return _status_to_string(self)


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
class IFF(IntFlag):
    """Dfu modes"""
    DFU = 0x0001  # /* DFU Mode, (not Runtime) */
    VENDOR = 0x0100
    PRODUCT = 0x0200
    CONFIG = 0x0400
    IFACE = 0x0800
    ALT = 0x1000
    DEVNUM = 0x2000
    PATH = 0x4000
    # DFU_IFF_DFU = 0x0001  /* DFU Mode, (not Runtime) */
    # DFU_IFF_ALT = 0x0002  /* Multiple alternate settings */

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self._name_}: 0x{self._value_:04x}>"


@dataclass
class StatusRetVal:
    """
    Converts dfu_get_status result bytes to applicable dataclass
    This is based off of DFU_GETSTATUS
    the data structure to be populated with the results
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
    path: [str, int] = None  # FIXME: deprecated
    flags: [IFF, int] = 0
    count: int = None  # FIXME: deprecated
    dev: usb.core.Device = None
    quirks: int = None
    bwPollTimeout: int = 0
    bMaxPacketSize0: int = 0
    serial_name: str = ""
    func_dfu: FuncDescriptor = None
    next: 'DfuIf' = None
    mem_layout: MemSegment = None


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
        return _detach(self.dev, self.interface, timeout)

    def download(self, transaction: int, data_or_length: [bytes, int]) -> int:
        """Binds self to dfu.download()"""
        return _download(self.dev, self.interface, transaction, data_or_length)

    def upload(self, transaction: int, data_or_length: [bytes, int]) -> bytes:
        """Binds self to dfu.upload()"""
        return _upload(self.dev, self.interface, transaction, data_or_length)

    def abort(self) -> int:
        """Binds self to dfu.abort()"""
        return _abort(self.dev, self.interface)

    def get_status(self) -> StatusRetVal:
        """Binds self to dfu.get_status()"""
        return _get_status(self.dev, self.interface)

    def clear_status(self) -> int:
        return _clear_status(self.dev, self.interface)

    def get_state(self) -> State:
        """Binds self to dfu.get_state()"""
        return _get_state(self.dev, self.interface)

    def abort_to_idle(self):
        """Binds self to dfu.abort_to_idle()"""
        return _abort_to_idle(self)


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


def debug(level: int) -> None:
    """
    NOTE: Maybe not needed cause python can define globals after
    :param level: logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # pylint: disable=global-statement
    global DEBUG_LEVEL
    DEBUG_LEVEL = level
    _logger.setLevel(level)


def _detach(device: usb.core.Device, interface: int, timeout: int) -> bytes:
    """
    DETACH Request (DFU Spec 1.0, Section 5.1)

    Sends to device command to switch it to DFU mode
    u have to free device and handle it again
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :param timeout: the timeout in ms the USB device should wait for a pending
    :return: bytes or < 0 on error
    """

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


def _download(device: usb.core.Device,
              interface: int,
              transaction: int,
              data_or_length: [bytes, int]) -> int:
    """
    DNLOAD Request (DFU Spec 1.0, Section 6.1.1)

    Download data to special page of DFU device
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :param transaction: start page int(total_data_size/xfer_size)
    :param data_or_length: the data to transfer
    :return: downloaded data or error code in bytes
    """

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


def _upload(device: usb.core.Device,
            interface: int,
            transaction: int,
            data_or_length: [bytes, int]) -> bytes:
    """
    UPLOAD Request (DFU Spec 1.0, Section 6.2)

    Uploads data from special page of DFU device
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :param transaction: start page int(total_data_size/xfer_size)
    :param data_or_length: the buffer to put the received data in
    :return: uploaded bytes or < 0 on error
    """

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


def _get_status(device: usb.core.Device, interface: int) -> StatusRetVal:
    """
     GETSTATUS Request (DFU Spec 1.0, Section 6.1.2)

    Returns DFU interface status
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :return: StatusRetVal
    """

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


def _clear_status(device: usb.core.Device, interface: int) -> int:
    """
    CLRSTATUS Request (DFU Spec 1.0, Section 6.1.3)

    Clears DFU interface status
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :return: return 0 or < 0 on an error
    """

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


def _get_state(device: usb.core.Device, interface: int) -> [State, int]:
    """
    GETSTATE Request (DFU Spec 1.0, Section 6.1.5)

    Returns DFU interface state
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :return: returns the state or < 0 on error
    """

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


def _abort(device: usb.core.Device, interface: int) -> int:
    """
    ABORT Request (DFU Spec 1.0, Section 6.1.4)

    Aborts DFU command
    :param device: the usb_dev_handle to communicate with
    :param interface: the interface to communicate with
    :return: returns 0 or < 0 on an error
    """

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


def _state_to_string(state: int) -> [str, None]:
    """
    :param state:
    :return: State name by State Enum
    """
    try:
        return _STATES_NAMES[State(state)]
    except (ValueError, KeyError):
        return None


def _status_to_string(status: int) -> [str, None]:
    """
    :param status:
    :return: State name by Status Enum
    """
    try:
        return _DFU_STATUS_NAMES[Status(status)]
    except (ValueError, KeyError):
        return None


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


def _abort_to_idle(dif: DfuIf):
    if dif.abort() < 0:
        _logger.error("Error sending dfu abort request")
        sys.exit(1)
    if (ret := int(dst := dif.get_status())) < 0:
        _logger.error("Error during abort get_status")
        sys.exit(1)
    if dst.bState != State.DFU_IDLE:
        _logger.error("Failed to enter idle state on abort")
        sys.exit(1)
    milli_sleep(dst.bwPollTimeout)
    return ret


# global definitions
DEBUG: int = 0

INVALID_DFU_TIMEOUT = -1

TIMEOUT: int = INVALID_DFU_TIMEOUT
TRANSACTION: int = 0

DEBUG_LEVEL: int = 0

__all__ = (
    "Command",
    "Status",
    "State",
    "StatusRetVal",
    "DfuIf",
    'IFF',
    'init'
)

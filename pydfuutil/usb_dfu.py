"""
USB Device Firmware Update Implementation for OpenPCD
Protocol definitions for USB DFU
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This ought to be compliant to the USB DFU Spec 1.0 as available from
https://www.usb.org/developers/devclass_docs/usbdfu10.pdf

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
import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag


import usb.util
USB_TYPE_DFU = usb.TYPE_CLASS | usb.RECIP_INTERFACE


USB_DT_DFU = 0x21
USB_DT_DFU_SIZE = 9


class BmAttributes(IntFlag):
    """Enum of DFU_FUNC_DESCRIPTOR's BmAttributes"""
    USB_DFU_CAN_DOWNLOAD = 1 << 0
    USB_DFU_CAN_UPLOAD = 1 << 1
    USB_DFU_MANIFEST_TOL = 1 << 2
    USB_DFU_WILL_DETACH = 1 << 3


# pylint: disable=invalid-name
@dataclass
class FuncDescriptor:
    """USB_DFU_FUNC_DESCRIPTOR's'"""
    bLength: int = 0
    bDescriptorType: int = 0
    bmAttributes: BmAttributes = 0
    wDetachTimeOut: int = 0
    wTransferSize: int = 0
    bcdDFUVersion: int = 0

    def __repr__(self) -> str:
        return (f"FuncDescriptor("
               f"bLength={self.bLength}, "
               f"bDescriptorType={self.bDescriptorType}, "
               f"bmAttributes={self.bmAttributes}, "
               f"wDetachTimeOut={self.wDetachTimeOut}, "
               f"wTransferSize={self.wTransferSize}, "
               f"bcdDFUVersion=0x{self.bcdDFUVersion:04x})")

    @staticmethod
    def from_bytes(data: [bytes, bytearray]) -> 'FuncDescriptor':
        """parse bytes to a FuncDescriptor"""
        func_dfu = FuncDescriptor()
        (func_dfu.bLength,
         func_dfu.bDescriptorType,
         bmAttributes,
         func_dfu.wDetachTimeOut,
         func_dfu.wTransferSize,
         func_dfu.bcdDFUVersion) = struct.unpack(
            '<BBBHHH', data)

        func_dfu.bmAttributes = BmAttributes(bmAttributes)
        return func_dfu



# DFU class-specific requests (Section 3, DFU Rev 1.1)
class UsbReqDfu(IntEnum):
    """Dfu requests"""
    DETACH = 0x00
    DNLOAD = 0x01
    UPLOAD = 0x02
    GETSTATUS = 0x03
    CLRSTATUS = 0x04
    GETSTATE = 0x05
    ABORT = 0x06


# DFU_GETSTATUS bStatus values (Section 6.1.2, DFU Rev 1.1)
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

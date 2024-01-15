"""
USB Device Firmware Update Implementation for OpenPCD
Protocol definitions for USB DFU
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This ought to be compliant to the USB DFU Spec 1.0 as available from
http://www.usb.org/developers/devclass_docs/usbdfu10.pdf
"""

from enum import IntEnum

import usb.util
from construct import FlagsEnum, Byte, Int8ul, Struct, Int16ul

USB_DT_DFU = 0x21

bmAttributes = FlagsEnum(
    Byte,
    USB_DFU_CAN_DOWNLOAD=0x1,  # is support updates
    USB_DFU_CAN_UPLOAD=0x2,  # is prog warranty ok
    USB_DFU_MANIFEST_TOL=0x4,
    USB_DFU_WILL_DETACH=0x8,
)

USB_DFU_FUNC_DESCRIPTOR = Struct(
    bLength=Int8ul,
    bDescriptorType=Int8ul,
    bmAttributes=bmAttributes,
    wDetachTimeOut=Int16ul,
    wTransferSize=Int16ul,
    bcdDFUVersion=Int16ul,
)

USB_DT_DFU_SIZE = 9

USB_TYPE_DFU = usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE


# DFU class-specific requests (Section 3, DFU Rev 1.1)
class USB_REQ_DFU(IntEnum):
    """Dfu requests"""
    DETACH = 0x00
    DNLOAD = 0x01
    UPLOAD = 0x02
    GETSTATUS = 0x03
    CLRSTATUS = 0x04
    GETSTATE = 0x05
    ABORT = 0x06


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

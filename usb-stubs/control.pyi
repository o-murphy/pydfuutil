# Copyright 2009-2017 Wander Lairson Costa
# Copyright 2009-2021 PyUSB contributors
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

r"""usb.control - USB standard control requests

This module exports:

get_status - get recipeint status
clear_feature - clear a recipient feature
set_feature - set a recipient feature
get_descriptor - get a device descriptor
set_descriptor - set a device descriptor
get_configuration - get a device configuration
set_configuration - set a device configuration
get_interface - get a device interface
set_interface - set a device interface
"""

__author__: str

__all__ = [
    "DEVICE_REMOTE_WAKEUP",
    "ENDPOINT_HALT",
    "FUNCTION_SUSPEND",
    "LTM_ENABLE",
    "U1_ENABLE",
    "U2_ENABLE",
    "clear_feature",
    "get_configuration",
    "get_descriptor",
    "get_interface",
    "get_status",
    "set_configuration",
    "set_descriptor",
    "set_feature",
    "set_interface",
]

import array

import usb.core
from usb import core

USBError = core.USBError

def _parse_recipient(
    recipient: usb.core.Interface | usb.core.Endpoint | None, direction: int
) -> tuple[int, int]: ...

# standard feature selectors from USB 2.0/3.0
ENDPOINT_HALT: int
FUNCTION_SUSPEND: int
DEVICE_REMOTE_WAKEUP: int
U1_ENABLE: int
U2_ENABLE: int
LTM_ENABLE: int

def get_status(
    dev: usb.core.Device,
    recipient: usb.core.Interface | usb.core.Endpoint | None = None,
) -> int:
    r"""Return the status for the specified recipient.

    dev is the Device object to which the request will be
    sent to.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.

    The status value is returned as an integer with the lower
    word being the two bytes status value.
    """

def clear_feature(
    dev: usb.core.Device,
    feature: int,
    recipient: usb.core.Interface | usb.core.Endpoint | None = None,
) -> None:
    r"""Clear/disable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to disable.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.
    """

def set_feature(
    dev: usb.core.Device,
    feature: int,
    recipient: usb.core.Interface | usb.core.Endpoint | None = None,
):
    r"""Set/enable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to enable.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.
    """

def get_descriptor(
    dev: usb.core.Device,
    desc_size: int,
    desc_type: int,
    desc_index: int,
    wIndex: int = 0,
) -> int | array.array:
    r"""Return the specified descriptor.

    dev is the Device object to which the request will be
    sent to.

    desc_size is the descriptor size.

    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """

def set_descriptor(
    dev: usb.core.Device,
    desc: int | bytes | bytearray,
    desc_type: int,
    desc_index: int,
    wIndex: int | None = None,
) -> None:
    r"""Update an existing descriptor or add a new one.

    dev is the Device object to which the request will be
    sent to.

    The desc parameter is the descriptor to be sent to the device.
    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """

def get_configuration(dev: usb.core.Device) -> int | bytes:
    r"""Get the current active configuration of the device.

    dev is the Device object to which the request will be
    sent to.

    This function differs from the Device.get_active_configuration
    method because the later may use cached data, while this
    function always does a device request.
    """

def set_configuration(dev: usb.core.Device, bConfigurationNumber: int) -> None:
    r"""Set the current device configuration.

    dev is the Device object to which the request will be
    sent to.
    """

def get_interface(dev: usb.core.Device, bInterfaceNumber: int) -> int | bytes:
    r"""Get the current alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """

def set_interface(
    dev: usb.core.Device, bInterfaceNumber: int, bAlternateSetting: int
) -> None:
    r"""Set the alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """

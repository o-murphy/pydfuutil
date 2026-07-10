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

r"""usb.legacy - backward compatibility layer with PyUSB 0.x

Minimal stub covering the module-level constants re-exported
by `usb/__init__.py` via `from usb.legacy import *`.
"""

CLASS_AUDIO: int
CLASS_COMM: int
CLASS_DATA: int
CLASS_HID: int
CLASS_HUB: int
CLASS_MASS_STORAGE: int
CLASS_PER_INTERFACE: int
CLASS_PRINTER: int
CLASS_WIRELESS_CONTROLLER: int
CLASS_VENDOR_SPEC: int
DT_CONFIG: int
DT_CONFIG_SIZE: int
DT_DEVICE: int
DT_DEVICE_SIZE: int
DT_ENDPOINT: int
DT_ENDPOINT_AUDIO_SIZE: int
DT_ENDPOINT_SIZE: int
DT_HID: int
DT_HUB: int
DT_HUB_NONVAR_SIZE: int
DT_INTERFACE: int
DT_INTERFACE_SIZE: int
DT_PHYSICAL: int
DT_REPORT: int
DT_STRING: int
ENDPOINT_ADDRESS_MASK: int
ENDPOINT_DIR_MASK: int
ENDPOINT_IN: int
ENDPOINT_OUT: int
ENDPOINT_TYPE_BULK: int
ENDPOINT_TYPE_CONTROL: int
ENDPOINT_TYPE_INTERRUPT: int
ENDPOINT_TYPE_ISOCHRONOUS: int
ENDPOINT_TYPE_MASK: int
ERROR_BEGIN: int
MAXALTSETTING: int
MAXCONFIG: int
MAXENDPOINTS: int
MAXINTERFACES: int
PROTOCOL_BLUETOOTH_PRIMARY_CONTROLLER: int
RECIP_DEVICE: int
RECIP_ENDPOINT: int
RECIP_INTERFACE: int
RECIP_OTHER: int
REQ_CLEAR_FEATURE: int
REQ_GET_CONFIGURATION: int
REQ_GET_DESCRIPTOR: int
REQ_GET_INTERFACE: int
REQ_GET_STATUS: int
REQ_SET_ADDRESS: int
REQ_SET_CONFIGURATION: int
REQ_SET_DESCRIPTOR: int
REQ_SET_FEATURE: int
REQ_SET_INTERFACE: int
REQ_SYNCH_FRAME: int
SUBCLASS_RF_CONTROLLER: int
TYPE_CLASS: int
TYPE_RESERVED: int
TYPE_STANDARD: int
TYPE_VENDOR: int

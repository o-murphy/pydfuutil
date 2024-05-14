# PyDfuUtil - Pure python fork of **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)** wrappers to **[libusb](https://github.com/libusb/libusb)**

[![PyPI Version](https://img.shields.io/pypi/v/pydfuutil?label=PyPI&logo=pypi)](https://pypi.org/project/pydfuutil/)

## Table of contents
* **[Introduction](#introduction)**
* **[Requirements](#requirements-and-platform-support)**
* **[Installing](#installing)**
* **[Todos](#todos)**
* **[Getting help](#getting-help)**
* **[About](#about)**
* **[Footnotes](#footnotes)**


## Introduction

* **PyDFUUtil** provides for easy access to the devices that supports **DFU** interface over host machine's **Universal Serial Bus (USB)**
system for Python 3.
* **PyDFUUtil** is an open realisation of original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**
and thin wrapper over **[libusb](https://github.com/libusb/libusb)** _(uses **[PyUsb](https://github.com/pyusb/pyusb)** library as a backend)_.

> [!WARNING]
> The current status of the project is BETA version.
> Use it for your own risk

> [!TIP]
> Searching for contributors for testing the library

## Requirements and platform support

* Since **PyDFUUtil** uses the **[libusb](https://github.com/libusb/libusb)** library it has similar dependencies for using **[libusb](https://github.com/libusb/libusb)**
* **PyDFUUtil** primarily tested on Linux and Windows, 
but also can work on each platform where **[PyUsb](https://github.com/construct/construct)** library are available, including MacOS


> [!IMPORTANT]
> Current version implements but not tested with real `dfuse` devices!


## Installing

**PyDFUUtil** is generally installed through pip

    # the latest official release
    python -m pip install pydfuutil

    # install a specific version (e.g. 0.0.1b1)
    python -m pip install pydfuutil==0.0.1b1

## Usage

### dfu-util
```Bash
pydfuutil -h 
# or
python -m pydfuutil -h

####### usage:
usage: pydfuutil [-h] [-V] [-v] [-l] [-e] [-E <seconds>]
                 [-d <vid>:<pid>[,<vid_dfu>:<pid_dfu>]] [-n <dnum>] [-p <bus-port. ... .port>]
                 [-c <config_nr>] [-i <intf_nr>] [-S <serial_str>[,<serial_str_dfu>]]
                 [-a <alt>] [-t <size>] [-U <file>] [-Z <bytes>] [-D <file>] [-R] [-w]
                 [-s <address><:...>]

Python implementation of DFU-Util tools

options:
  -h, --help            show this help message and exit
  -V, --version         Print the version number
  -v, --verbose         Print verbose debug statements
  -l, --list            List the currently attached DFU capable USB devices
  -e, --detach          Detach the currently attached DFU capable USB devices
  -E <seconds>, --detach-delay <seconds>
                        Time to wait before reopening a device after detach
  -d <vid>:<pid>[,<vid_dfu>:<pid_dfu>], --device <vid>:<pid>[,<vid_dfu>:<pid_dfu>]
                        Specify Vendor/Product ID(s) of DFU device
  -n <dnum>, --devnum <dnum>
                        Match given device number (devnum from --list)
  -p <bus-port. ... .port>, --path <bus-port. ... .port>
                        Specify path to DFU device
  -c <config_nr>, --cfg <config_nr>
                        Specify the Configuration of DFU device
  -i <intf_nr>, --intf <intf_nr>
                        Specify the DFU Interface number
  -S <serial_str>[,<serial_str_dfu>], --serial <serial_str>[,<serial_str_dfu>]
                        Specify Serial String of DFU device
  -a <alt>, --alt <alt>
                        Specify the Altsetting of the DFU Interface
  -t <size>, --transfer-size <size>
                        Specify the number of bytes per USB Transfer
  -U <file>, --upload <file>
                        Read firmware from device into <file>
  -Z <bytes>, --upload-size <bytes>
                        Read firmware from device into <file>
  -D <file>, --download <file>
                        Read firmware from device into <file>
  -R, --reset           Issue USB Reset signalling once we`re finished
  -w, --wait            Wait for device to appear
  -s <address><:...>, --dfuse-address <address><:...>
                        ST DfuSe mode string, specifying target
                        address for raw file download or upload
                        (not applicable for DfuSe file (.dfu) downloads).
                        Add more DfuSe options separated with ':'

                        leave
                                Leave DFU mode (jump to application)
                        mass-erase
                                Erase the whole device (requires "force")
                        unprotect
                                Erase read protected device (requires "force")
                        will-reset
                                Expect device to reset (e.g. option bytes write)
                        force
                                You really know what you are doing!
                        <length>
                                Length of firmware to upload from device
```

### dfu-suffix
```Bash
pydfuutil-suffix -h
# or 
python -m pydfuutil.suffix -h


usage: dfu-suffix [-h] [-V] (-c | -a | -D) [-p <productID>] [-v <vendorID>] [-d <deviceID>] [-s <address>] [-T] <file>

positional arguments:
  <file>                Target filename

options:
  -h, --help            Print this help message
  -V, --version         Print the version number
  -c, --check           Check DFU suffix of <file>
  -a, --add             Add DFU suffix to <file>
  -D, --delete          Delete DFU suffix from <file>
  -p <productID>, --pid <productID>
                        Add product ID into DFU suffix in <file>
  -v <vendorID>, --vid <vendorID>
                        Add vendor ID into DFU suffix in <file>
  -d <deviceID>, --did <deviceID>
                        Add device ID into DFU suffix in <file>
  -s <address>, --stellaris-address <address>
                        Specify lmdfu address for LMDFU_ADD
  -T, --stellaris       Set lmdfu mode to LMDFU_CHECK

```

#### Done:
- [x] dfu
- [x] dfu_file
- [x] dfu_load
- [x] portable
- [x] quirks
- [x] suffix
- [x] usb_dfu
- [x] lmdfu
- [x] dfuse_mem
- [x] dfuse
- [x] dfu-util

#### Todo
- [x] Update sources to latest original version "dfu-util-0.11"

[//]: # (https://dfu-util.sourceforge.net/)
[//]: # (- https://sourceforge.net/p/dfu-util/dfu-util/ci/master/tree/)


## Getting help
* To report a bug or propose a new feature, use our issue tracker. But please search the database before opening a new issue.

## About
Dfu-util - Device Firmware Upgrade Utilities

Dfu-util is the host side implementation of the 
[DFU 1.0](http://www.usb.org/developers/devclass_docs/usbdfu10.pdf) and 
[DFU 1.1](http://www.usb.org/developers/devclass_docs/DFU_1.1.pdf)
specification of the USB forum.

DFU is intended to download and upload firmware to devices connected over
USB. It ranges from small devices like micro-controller boards up to mobile
phones. With dfu-util you are able to download firmware to your device or
upload firmware from it.

dfu-util has been tested with Openmoko Neo1973 and Freerunner and many
other devices.

* **[The official website](http://dfu-util.gnumonks.org)**
* **[DFU 1.0 spec](http://www.usb.org/developers/devclass_docs/usbdfu10.pdf)**
* **[DFU 1.1 spec](http://www.usb.org/developers/devclass_docs/DFU_1.1.pdf)**

## RISK NOTICE
> [!IMPORTANT]
> THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

## Footnotes
* On systems that still default to Python 2, replace python with python3
* Project is in develop, it fulls issues not according to original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**!


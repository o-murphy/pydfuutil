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
* It uses python **[construct](https://github.com/construct/construct)** library for simple unpacking C-structs.
* **PyDFUUtil** primarily tested on Linux and Windows, 
but also can work on each platform where **[PyUsb](https://github.com/construct/construct)** and **[construct](https://github.com/construct/construct)** libraries are available, including MacOS


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
usage: pydfuutil [-h] [-V] [-v] [-l] [-e] [-d VID:PID] [-p BUS-PORT] [-c CONFIG_NR] [-i INTF_NR] [-a ALT] [-t SIZE] [-U FILE] [-D FILE] [-R] [-s ADDRESS]

Python implementation of DFU-Util tools

options:
  -h, --help            show this help message and exit
  -V, --version         Print the version number
  -v, --verbose         Print verbose debug statements
  -l, --list            List the currently attached DFU capable USB devices
  -e, --detach          Detach the currently attached DFU capable USB devices
  -d VID:PID, --device VID:PID
                        Specify Vendor/Product ID of DFU device
  -p BUS-PORT, --path BUS-PORT
                        Specify path to DFU device
  -c CONFIG_NR, --cfg CONFIG_NR
                        Specify the Configuration of DFU device
  -i INTF_NR, --intf INTF_NR
                        Specify the DFU Interface number
  -a ALT, --alt ALT     Specify the Altsetting of the DFU Interface
  -t SIZE, --transfer-size SIZE
                        Specify the number of bytes per USB Transfer
  -U FILE, --upload FILE
                        Read firmware from device into <file>
  -D FILE, --download FILE
                        Write firmware from <file> into device
  -R, --reset           Issue USB Reset signalling once we`re finished
  -s ADDRESS, --dfuse-address ADDRESS
                        ST DfuSe mode, specify target address for raw file download or upload. Not applicable for DfuSe file (.dfu) downloads
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


## Todos

#### Modules to implement:

- [ ] main
  - [x] atoi()
  - [ ] usb_path2devnum()
  - [x] find_dfu_if()
  - [x] _get_first_cb()
  - [x] _get_first_dfu_if()
  - [x] _check_match_cb()
  - [x] get_matching_dfu_if()
  - [x] _count_match_cb()
  - [x] count_matching_dfu_if()
  - [x] get_alt_name()
  - [x] print_dfu_if()
  - [x] list_dfu_interfaces()
  - [x] alt_by_name()
  - [x] _count_cb()
  - [x] count_dfu_interfaces()
  - [x] iterate_dfu_devices()
  - [x] found_dfu_device()
  - [x] get_first_dfu_device()
  - [x] count_one_dfu_device()
  - [x] count_dfu_devices()
  - [x] parse_vendprod()
  - [ ] resolve_device_path()
  - [x] find_descriptor()
  - [ ] usb_get_any_descriptor()
  - [x] get_cached_extra_descriptor()
  - [x] help_()
  - [x] print_version()
  - [ ] main()
- [ ] dfu_load.PROGRESS_BAR -> rich.Progress


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
* Project is in develop, it fulls of not implemented statements that's not according to original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**!


# PyDfuUtil - Pure python fork of **[dfu-util](https://dfu-util.sourceforge.net/)** wrappers to **[libusb](https://github.com/libusb/libusb)**

[![PyPI Version](https://img.shields.io/pypi/v/pydfuutil?label=PyPI&logo=pypi)](https://pypi.org/project/pydfuutil/)

## Table of contents
* **[Introduction](#introduction)**
* **[Requirements](#requirements-and-platform-support)**
* **[Installing](#installing)**
* **[Usage](#installing)**
  + [**Manual page**](https://dfu-util.sourceforge.net/dfu-util.1.html)
  + [**dfu-util** (pydfuutil-util)](#pydfuutil)
  + [**dfu-suffix** (pydfuutil-suffix)](#pydfuutil-suffix)
  + [**dfu-prefix** (pydfuutil-prefix)](#pydfuutil-prefix)
  + [**lsusb** (pydfuutil-lsusb)](#pydfuutil-lsusb)
* **[Todos](#todos)**
* **[Getting help](#getting-help)**
* **[About](#about)**
* **[Footnotes](#footnotes)**


## Introduction

* **PyDFUUtil** provides for easy access to the devices that supports **DFU** interface over host machine's **Universal Serial Bus (USB)**
system for Python 3.
* **PyDFUUtil** is an open realisation of original **[dfu-util](https://dfu-util.sourceforge.net/)**
and thin wrapper over **[libusb](https://github.com/libusb/libusb)** _(uses **[PyUsb](https://github.com/pyusb/pyusb)** library as a backend)_.

> [!WARNING]
> The current status of the project is BETA version.
> Use it for your own risk

> [!IMPORTANT]
> Current version implements but not tested with real `dfuse` devices!

> [!TIP]
> Searching for contributors for testing the library

## Requirements and platform support

* Since **PyDFUUtil** uses the **[libusb](https://github.com/libusb/libusb)** library it has similar dependencies for using **[libusb](https://github.com/libusb/libusb)**
* **PyDFUUtil** primarily tested on Linux and Windows, 
but also can work on each platform where **[PyUsb](https://github.com/construct/construct)** library are available, including MacOS


## Installing

**PyDFUUtil** is generally installed through pip

    # the latest official release
    python -m pip install pydfuutil

    # install a specific version (e.g. 0.0.1b1)
    python -m pip install pydfuutil==0.0.1b1

## Usage

### pydfuutil
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

### pydfuutil-suffix
```Bash
pydfuutil-suffix -h
# or 
python -m pydfuutil.suffix -h

####### usage:
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

### pydfuutil-prefix
```Bash
pydfuutil-prefix -h
# or 
python -m pydfuutil.prefix -h

####### usage:
usage: pydfuutil-prefix [-h] [-V] (-c | -D | -a) [-s <address>] [-T]
                        [-L]
                        <file>


positional arguments:
  <file>                Target filename

options:
  -h, --help            show this help message and exit
  -V, --version         Print the version number
  -c, --check           Check DFU suffix of <file>
  -D, --delete          Delete DFU suffix from <file>
  -a, --add             Add DFU suffix to <file>

In combination with -a:
  -s <address>, --stellaris-address <address>
                        Add TI Stellaris address prefix to <file>

In combination with -a or -D or -c:
  -T, --stellaris       Act on TI Stellaris address prefix of <file>

In combination with -a or -D or -c:
  -L, --lpc-prefix      Use NXP LPC DFU prefix format
```

### pydfuutil-lsusb
```Bash
pydfuutil-lsusb -h
# or 
python -m pydfuutil.lsusb -h

####### usage:
usage: pydfuutil-prefix [-v] [-s [[bus]:][devnum]]
                        [-d vendor:[product]] [-D device] [-t] [-V]    
                        [-h]

options:
  -v, --verbose        Increase verbosity (show descriptors)
  -s [[bus]:][devnum]  Show only devices with specified device and/or  
                       bus numbers (in decimal)
  -d vendor:[product]  Show only devices with the specified vendor     
                       and product ID numbers (in hexadecimal)
  -D device            Selects which device lsusb will examine by      
                       UNIX-like path simulate
  -t, --tree           Simulate UNIX-like physical USB device
                       hierarchy
  -V, --version        Print the version number
  -h, --help           Show this help message and exit
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

* **[The official website](https://dfu-util.sourceforge.net/)**
* **[DFU 1.0 spec](http://www.usb.org/developers/devclass_docs/usbdfu10.pdf)**
* **[DFU 1.1 spec](http://www.usb.org/developers/devclass_docs/DFU_1.1.pdf)**

## RISK NOTICE
> [!IMPORTANT]
> THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

## Footnotes
* On systems that still default to Python 2, replace python with python3
* Project is in develop, it fulls issues not according to original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**!


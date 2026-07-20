# PyDfuUtil - Pure python fork of **[dfu-util](https://dfu-util.sourceforge.net/)** wrappers to **[libusb](https://github.com/libusb/libusb)**

![license]
[![pypi]][PyPiUrl]
![py-versions]
[![coverage]][CodecovUrl]

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
* **[Library usage](#library-usage)**
* **[Todos](#todos)**
* **[Known bugs and workarounds](#known-bugs-and-workarounds)**
* **[Getting help](#getting-help)**
* **[About](#about)**
* **[Footnotes](#footnotes)**


## Introduction

* **PyDFUUtil** provides for easy access to the devices that supports **DFU** interface over host machine's **Universal Serial Bus (USB)**
system for Python 3.
* **PyDFUUtil** is an open realisation of original **[dfu-util](https://dfu-util.sourceforge.net/)**
and thin wrapper over **[libusb](https://github.com/libusb/libusb)** _(uses **[PyUsb](https://github.com/pyusb/pyusb)** library as a backend)_.
* Tracks the **master** branch of the upstream **[dfu-util](https://git.code.sf.net/p/dfu-util/dfu-util)**
C sources for feature/behavioral parity — see [docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md](docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md)
for the itemized audit against it.

> [!WARNING]
> Use it for your own risk

> [!IMPORTANT]
> Current version implements but not tested with real `dfuse` devices!

> [!TIP]
> Searching for contributors for testing the library

## Requirements and platform support

* Since **PyDFUUtil** uses the **[libusb](https://github.com/libusb/libusb)** library it has similar dependencies for using **[libusb](https://github.com/libusb/libusb)**
* **PyDFUUtil** primarily tested on Linux and Windows, 
but also can work on each platform where **[PyUsb](https://github.com/construct/construct)** library are available, including MacOS
* **[libusb-package](https://github.com/pyocd/libusb-package)** (a bundled, platform-independent
`libusb` binary) is an *optional* dependency, installed via the `libusb` extra
(`pip install pydfuutil[libusb]`). Install it on platforms that don't already provide a system
`libusb`; otherwise **PyDFUUtil** falls back to **PyUsb**'s own system `libusb` search.


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

## Library usage

**PyDFUUtil** isn't just the four `pydfuutil-*` CLI entry points above — each of them is a thin
`argparse` wrapper around a plain, importable Python API in the `pydfuutil` package. The CLI
tools' own source (`pydfuutil/__main__.py`, `suffix.py`, `prefix.py`, `lsusb.py`) is itself the
most complete, always-up-to-date reference for driving the API directly.

### Inspecting a DFU file

```python
from pydfuutil.dfu_file import DfuFile, SuffixReq, PrefixReq

file = DfuFile(name="firmware.dfu")
file.load(SuffixReq.MAYBE_SUFFIX, PrefixReq.MAYBE_PREFIX)

print(f"Vendor:  0x{file.idVendor:04x}")
print(f"Product: 0x{file.idProduct:04x}")
print(f"Size:    {file.size.total} bytes")

file.show_suffix_and_prefix()  # same output as `pydfuutil-suffix -c`/`pydfuutil-prefix -c`
```

### Listing attached DFU-capable devices

```python
import usb.core
from pydfuutil.dfu_util import probe_devices, list_dfu_interfaces

ctx = list(usb.core.find(find_all=True))
probe_devices(ctx)       # populates DfuUtil.dfu_root as a side effect
list_dfu_interfaces()    # prints the same table as `pydfuutil -l`
```

### Uploading/downloading firmware

The full runtime→DFU-mode transition, device claiming, and the plain-DFU/DfuSe upload/download
dispatch (`pydfuutil.dfu`, `pydfuutil.dfu_load`, `pydfuutil.dfuse`) are involved enough — and
device/quirk-dependent enough — that `pydfuutil/__main__.py::main()` is the canonical, tested
example to copy from rather than a shortened README snippet that could drift out of sync with it.

> [!TIP]
> Every module in `pydfuutil/` docstrings/type-hints its public functions; `import pydfuutil.dfu`,
> `pydfuutil.dfu_load`, `pydfuutil.dfuse`, and `pydfuutil.quirks` and read the corresponding
> `do_upload`/`do_download` functions alongside `main.c`/`dfuse.c` in the upstream
> [dfu-util source](https://git.code.sf.net/p/dfu-util/dfu-util) if you're embedding this in your
> own tool.

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


## Known bugs and workarounds

**PyDFUUtil** is regularly audited function-by-function against the upstream C `dfu-util` source
to catch behavioral divergences introduced during the port; the full, itemized log — including
items deliberately left unfixed with the reasoning why — lives in
[docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md](docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md). A couple of
findings are pre-existing bugs in *upstream* `dfu-util` itself, faithfully reproduced here rather
than "fixed" out of sync with the reference implementation:

* **"Check for DFU mode device" guard is a permanent no-op.** Upstream's `main.c` (and this
  port's `__main__.py`) use `flags | DFU_IFF_DFU` where `flags & DFU_IFF_DFU` was clearly
  intended; ORing with the nonzero `DFU_IFF_DFU` bit is always truthy, so the guard can never
  actually raise "Device is not in DFU mode". Left as-is for parity with upstream.
* **`-w`/`--wait` argument-arity inconsistency in upstream's long-option table.** Upstream declares
  `--wait` as taking a required argument in its `getopt_long` table, but the short option string
  and the actual handler never read one. This port's `-w`/`--wait` is a clean no-argument flag for
  both forms — arguably a correction rather than a regression, so no change is planned to match
  upstream's inconsistency here.

See the "Needs human judgment" section of the backlog doc for the full analysis of these and a
couple of other borderline/rare-edge-case items.

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


<!-- REUSABLE LINKS -->

[license]:
https://img.shields.io/github/license/o-murphy/pydfuutil

[pypi]:
https://img.shields.io/pypi/v/pydfuutil?label=PyPI&logo=pypi

[PyPiUrl]:
https://pypi.org/project/pydfuutil/

[py-versions]:
https://img.shields.io/pypi/pyversions/pydfuutil

[coverage]:
https://codecov.io/gh/o-murphy/pydfuutil/graph/badge.svg

[CodecovUrl]:
https://codecov.io/gh/o-murphy/pydfuutil


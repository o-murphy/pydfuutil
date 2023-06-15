# PyDfuUtil - Pure python realisation of **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)** wrappers to **[libusb](https://github.com/libusb/libusb)**

Introduction
------------

* **PyDFUUtil** provides for easy access to the devices that supports **DFU** interface over host machine's **Universal Serial Bus (USB)**
system for Python 3.
* **PyDFUUtil** is an open realisation of original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**
and thin wrapper over **[libusb](https://github.com/libusb/libusb)** _(uses **[PyUsb](https://github.com/pyusb/pyusb)** library as a backend)_.


Requirements and platform support
---------------------------------

* Since **PyDFUUtil** uses the **[libusb](https://github.com/libusb/libusb)** library it has similar dependencies for using **[libusb](https://github.com/libusb/libusb)**
* It uses python **[construct](https://github.com/construct/construct)** library for simple unpacking C-structs.
* **PyDFUUtil** primarily tested on Linux and Windows, 
but also can work on each platform where **[PyUsb](https://github.com/construct/construct)** and **[construct](https://github.com/construct/construct)** libraries are available, including MacOS

Installing
----------

**PyDFUUtil** is generally installed through pip

    # the latest official release
    python -m pip install pydfuutil

    # install a specific version (e.g. 0.0.1b1)
    python -m pip install pydfuutil==0.0.1b1

Getting help
------------
* To report a bug or propose a new feature, use our issue tracker. But please search the database before opening a new issue.

Footnotes
---------
* On systems that still default to Python 2, replace python with python3
* Project is in develop, it fulls of not implemented statements that's not according to original **[dfu-util](https://github.com/Stefan-Schmidt/dfu-util)**!

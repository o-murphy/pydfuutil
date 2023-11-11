"""
pydfuutil
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)
Based on existing code of dfu-programmer-0.4
"""
import usb.core

from pydfuutil import __version__, __copyright__


# TODO: not implemented yet

def find_dfu_if(  # libusb_device: usb.core.Device, ...
) -> int:
    """
    Find DFU interfaces in a given device.
    Iterate through all DFU interfaces and their alternate settings
    and call the passed handler function on each setting until handler
    TODO: implement
    :param libusb_device:
    TODO: annotations
    :return: non-zero
    """
    raise NotImplementedError


def _get_first_cb(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def get_first_dfu_if(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    return find_dfu_if(
        # ...
    )


def _check_match_cb(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def get_matching_dfu_if(  # ...
) -> int:
    """
    Fills in dif from the matching DFU interface/altsetting
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def _count_match_cb(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def count_matching_dfu_if(  # ...
) -> int:
    """
    Count matching DFU interface/altsetting
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def get_alt_name(  # ...
) -> int:
    """
    Retrieves alternate interface name string.
    TODO: implement
    :param
    :return: string length, or negative on error
    """
    raise NotImplementedError


def print_dfu_if(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def list_dfu_interfaces(  # ...
) -> int:
    """
    Walk the device tree and print out DFU devices
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def alt_by_name(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return: altsetting+1 so that we can use return value 0 to indicate "not found"
    """
    raise NotImplementedError


def _count_cb(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def count_dfu_interfaces(dev: usb.core.Device,
                         # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    num_found = 0
    find_dfu_if(
        # dev
    )
    raise NotImplementedError


def iterate_dfu_devices(  # ...
) -> int:
    """
    Iterate over all matching DFU capable devices within system
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def found_dfu_device(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def get_first_dfu_device(  # ...
) -> int:
    """
    Find the first DFU-capable device, save it in dfu_if->dev
    TODO: implement
    :param
    :return:
    """
    return iterate_dfu_devices(
        # ...
    )


def count_one_dfu_device(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def count_dfu_devices(  # ...
) -> int:
    """
    Count DFU capable devices within system
    TODO: implement
    :param
    :return:
    """
    num_found = 0
    raise NotImplementedError


def parse_vendprod(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


# TODO this function definition is conditional
def resolve_device_path(  # ...
) -> int:
    """
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def find_descriptor(  # ...
) -> int:
    """
    Look for a descriptor in a concatenated descriptor list
    Will return desc_index'th match of given descriptor type
    TODO: implement
    :param
    :return: length of found descriptor, limited to res_size
    """
    raise NotImplementedError


def usb_get_any_descriptor(  # ...
) -> int:
    """
    Look for a descriptor in the active configuration
    Will also find extra descriptors which are normally
    not returned by the standard libusb_get_descriptor()
    TODO: implement
    :param
    :return:
    """
    raise NotImplementedError


def get_cached_extra_descriptor(  # ...
) -> int:
    """
    Get cached extra descriptor from libusb for an interface
    TODO: implement
    :param
    :return: length of found descriptor
    """
    raise NotImplementedError


def help() -> None:
    print(
        "  -h --help\t\t\tPrint this help message\n"
        "  -V --version\t\t\tPrint the version number\n"
        "  -v --verbose\t\t\tPrint verbose debug statements\n"
        "  -l --list\t\t\tList the currently attached DFU capable USB devices\n"
    )
    print(
        "  -e --detach\t\t\tDetach the currently attached DFU capable USB devices\n"
        "  -d --device vendor:product\tSpecify Vendor/Product ID of DFU device\n"
        "  -p --path bus-port. ... .port\tSpecify path to DFU device\n"
        "  -c --cfg config_nr\t\tSpecify the Configuration of DFU device\n"
        "  -i --intf intf_nr\t\tSpecify the DFU Interface number\n"
        "  -a --alt alt\t\t\tSpecify the Altsetting of the DFU Interface\n"
        "\t\t\t\tby name or by number\n"
    )
    print(
        "  -t --transfer-size\t\tSpecify the number of bytes per USB Transfer\n"
        "  -U --upload file\t\tRead firmware from device into <file>\n"
        "  -D --download file\t\tWrite firmware from <file> into device\n"
        "  -R --reset\t\t\tIssue USB Reset signalling once we're finished\n"
        "  -s --dfuse-address address\tST DfuSe mode, specify target address for\n"
        "\t\t\t\traw file download or upload. Not applicable for\n"
        "\t\t\t\tDfuSe file (.dfu) downloads\n"
    )


def print_version() -> None:
    print(f"{__version__}\n\n")
    print('Copyright 2005-2008 Weston Schmidt, Harald Welte and OpenMoko Inc.\n'
          f'{__copyright__}\n'
          'This program is Free Software and has ABSOLUTELY NO WARRANTY\n\n')


def main(argv):
    # Todo: implement
    raise NotImplementedError


if __name__ == '__main__':
    import sys

    main(sys.argv)

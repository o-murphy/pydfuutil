import dataclasses


@dataclasses.dataclass
class DFUFile:
    __slots__ = ['name', 'fileep', 'size', 'dwCRC', 'suffixlen',
                 'bcdDFU', 'idVendor', 'idProduct', 'bcdDevice']

    def __init__(self):
        """
        TODO: implementation
        """
        raise NotImplementedError("Feature not yet implemented")


def parse_dfu_suffix(file: DFUFile) -> int:
    """
    TODO: implementation
    :param file:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")


def generate_dfu_suffix(file: DFUFile) -> int:
    """
    TODO: implementation
    :param file:
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

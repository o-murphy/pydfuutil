from enum import IntEnum


class mode(IntEnum):
    MODE_NONE = 0x1
    MODE_ADD = 0x2
    MODE_DEL = 0x3
    MODE_CHECK = 0x4


class lmdfu_mode(IntEnum):
    LMDFU_NONE = 0x1
    LMDFU_ADD = 0x2
    LMDFU_DEL = 0x3
    LMDFU_CHECK = 0x4


def help_() -> None:
    print("Usage: dfu-suffix [options] <file>\n"
          "  -h --help\tPrint this help message\n"
          "  -V --version\tPrint the version number\n"
          "  -D --delete\tDelete DFU suffix from <file>\n"
          "  -p --pid\tAdd product ID into DFU suffix in <file>\n"
          "  -v --vid\tAdd vendor ID into DFU suffix in <file>\n"
          "  -d --did\tAdd device ID into DFU suffix in <file>\n"
          "  -c --check\tCheck DFU suffix of <file>\n"
          "  -a --add\tAdd DFU suffix to <file>"
          )
    print("  -s --stellaris-address <address>  Add TI Stellaris address "
          "prefix to <file>,\n\t\tto be used together with -a\n"
          "  -T --stellaris  Act on TI Stellaris extension prefix of "
          "<file>, to be used\n\t\tin combination with -D or -c"
          )


def print_version() -> None:
    """
    TODO: implementation
    :return:
    """
    raise NotImplementedError("Feature not yet implemented")

"""Pydfuutil exceptions."""


class GeneralError(Exception):
    """
    Usually indicates a general error.
    This can be used to indicate that the program
    encountered some issue during execution
    that prevented it from completing its task successfully.
    It can also be used as a catch-all for unspecified errors.
    """
    exit_code = 1


class DataError(GeneralError, ValueError, TypeError):
    exit_code = 65


class SoftwareError(GeneralError):
    exit_code = 70


class _IOError(GeneralError, IOError):
    exit_code = 74


class NoInputError(GeneralError, OSError):
    exit_code = 66


class UsbIOError(GeneralError):
    exit_code = 1


class GeneralWarning(GeneralError):
    """
    Usually indicates a general warning
    """


class MisuseError(GeneralError):
    """
    Often used to indicate misuse or incorrect usage of the program.
    For example, if the program receives
    invalid command-line arguments or options,
    it might exit with code 2 to indicate a syntax error.
    """
    exit_code = 2

class CapabilityError(GeneralError):
    """DFU incompatible usage error."""
    exit_code = 3
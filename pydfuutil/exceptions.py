"""Pydfuutil exceptions."""
import sys
from functools import wraps


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


class ProtocolError(GeneralError):
    exit_code = 76


class _IOError(GeneralError, IOError):
    exit_code = 74


class NoInputError(GeneralError, OSError):
    exit_code = 66


class UsbIOError(_IOError):
    exit_code = 1


class GeneralWarning(GeneralError):
    """
    Usually indicates a general warning
    """


class MissuseError(GeneralError):
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



def handle_exceptions(_logger):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, GeneralWarning):
                    if e.__str__():
                        _logger.warning(e)
                elif isinstance(e, GeneralError):
                    if e.__str__():
                        _logger.error(e)
                    sys.exit(e.exit_code)
                else:
                    _logger.exception("Unhandled exception occurred")
                    raise
        return wrapper
    return decorator



__all__ = (
    'GeneralError',
    'GeneralWarning',
    'NoInputError',
    'UsbIOError',
    'MissuseError',
    'CapabilityError',
    'DataError',
    'UsbIOError',
    '_IOError',
    'handle_exceptions'
)

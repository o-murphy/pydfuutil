"""
Pydfuutil exceptions.
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
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


class MissUseError(GeneralError):
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
    'MissUseError',
    'SoftwareError',
    'ProtocolError',
    'CapabilityError',
    'DataError',
    'UsbIOError',
    '_IOError',
    'handle_exceptions'
)

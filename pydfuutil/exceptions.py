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
import logging
import sys
from enum import IntEnum
from functools import wraps


class SysExit(IntEnum):
    OTHER = 1  # successful termination
    EX_OK = 0
    EX__BASE = 64  # base value for error messages
    EX_USAGE = 64  # command line usage error
    EX_DATAERR = 65  # data format error
    EX_NOINPUT = 66  # cannot open input
    EX_USER = 67  # addressee unknown
    EX_NOHOST = 68  # host name unknown
    EX_UNAVAILABLE = 69  # service unavailable
    EX_SOFTWARE = 70  # internal software error
    EX_OSERR = 71  # system error (e.g., can't fork)
    EX_OSFILE = 72  # critical OS file missing
    EX_CANTCREAT = 73  # can't create (user) output file
    EX_IOERR = 74  # input/output error
    EX_TEMPFAIL = 75  # temp failure; user is invited to retry
    EX_PROTOCOL = 76  # remote error in protocol
    EX_NOPERM = 77  # permission denied
    EX_CONFIG = 78  # configuration error
    EX_NOTFOUND = 79


class Errx(Exception):
    """
    Usually indicates a general error.
    This can be used to indicate that the program
    encountered some issue during execution
    that prevented it from completing its task successfully.
    It can also be used as a catch-all for unspecified errors.
    """
    exit_code = SysExit.OTHER

    def __init__(self, message, exit_code: SysExit = None):
        super().__init__(message)
        if isinstance(exit_code, SysExit):
            self.exit_code = exit_code


class DataError(Errx, ValueError, TypeError):
    """EX_DATAERR"""
    exit_code = SysExit.EX_DATAERR


class SoftwareError(Errx):
    """EX_SOFTWARE"""
    exit_code = SysExit.EX_SOFTWARE


class ProtocolError(Errx):
    """EX_PROTOCOL"""
    exit_code = SysExit.EX_PROTOCOL


class _IOError(Errx, IOError):
    """EX_IOERR"""
    exit_code = SysExit.EX_IOERR


class NoInputError(Errx, OSError):
    """EX_NOINPUT"""
    exit_code = SysExit.EX_NOINPUT


class UsbIOError(Errx, IOError):  # FIXME: Deprecated
    """USB IOError"""
    exit_code = SysExit.OTHER


class UsageError(Errx):
    """
    Often used to indicate misuse or incorrect usage of the program.
    For example, if the program receives
    invalid command-line arguments or options,
    it might exit with code 2 to indicate a syntax error.
    """
    exit_code = SysExit.EX_USAGE  # FIXME: maybe SystemExit + EX.EX_USAGE = 1


class CompatibilityError(Errx, OSError):
    """DFU incompatible usage error."""
    exit_code = 3  # OSError + EX_PROTOCOL = 3


def except_and_safe_exit(_logger: logging.Logger = None):
    """decorator to handle exceptions and exit safely"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Errx as e:
                if str(e) and _logger:
                    if _logger.level >= logging.DEBUG:
                        _logger.exception(e)
                    else:
                        _logger.error(e)
                sys.exit(e.exit_code)
            # pylint: disable=broad-exception-caught
            except Exception as e:
                if _logger.level >= logging.DEBUG:
                    _logger.exception(f"Unhandled exception occurred: {e}")
                else:
                    _logger.error(f"Unhandled exception occurred: {e}")
                sys.exit(1)

        return wrapper

    return decorator


__all__ = (
    'Errx',
    'NoInputError',
    'UsageError',
    'SoftwareError',
    'ProtocolError',
    'CompatibilityError',
    'DataError',
    'UsbIOError',
    '_IOError',
    'except_and_safe_exit'
)

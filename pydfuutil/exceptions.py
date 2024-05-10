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


class EX(IntEnum):
    UNDEFINED = -1
    EX_OK = 0
    EX_USAGE = 1
    EX_DATAERR = 65
    EX_NOINPUT = 66
    EX_NOUSER = 67
    EX_NOHOST = 68
    EX_UNAVAILABLE = 69
    EX_SOFTWARE = 70  # RuntimeError 70 or 1
    EX_OSERR = 71
    EX_OSFILE = 72
    EX_CANTCREAT = 73
    EX_IOERR = 74
    EX_TEMPFAIL = 75
    EX_PROTOCOL = 76  # or EX_PROTOCOL = 3
    EX_NOPERM = 77
    EX_CONFIG = 78
    EX_NOTFOUND = 79


# from sysexits.h
# #define EX_OK		0	/* successful termination */
#
# #define EX__BASE	64	/* base value for error messages */
#
# #define EX_USAGE	64	/* command line usage error */
# #define EX_DATAERR	65	/* data format error */
# #define EX_NOINPUT	66	/* cannot open input */
# #define EX_NOUSER	67	/* addressee unknown */
# #define EX_NOHOST	68	/* host name unknown */
# #define EX_UNAVAILABLE	69	/* service unavailable */
# #define EX_SOFTWARE	70	/* internal software error */
# #define EX_OSERR	71	/* system error (e.g., can't fork) */
# #define EX_OSFILE	72	/* critical OS file missing */
# #define EX_CANTCREAT	73	/* can't create (user) output file */
# #define EX_IOERR	74	/* input/output error */
# #define EX_TEMPFAIL	75	/* temp failure; user is invited to retry */
# #define EX_PROTOCOL	76	/* remote error in protocol */
# #define EX_NOPERM	77	/* permission denied */
# #define EX_CONFIG	78	/* configuration error */
#
# #define EX__MAX	78	/* maximum listed value */


class Errx(Exception):
    """
    Usually indicates a general error.
    This can be used to indicate that the program
    encountered some issue during execution
    that prevented it from completing its task successfully.
    It can also be used as a catch-all for unspecified errors.
    """
    exit_code = EX.UNDEFINED
    def __init__(self, message, exit_code: EX = None):
        super().__init__(message)
        if isinstance(exit_code, EX):
            self.exit_code = exit_code


class DataError(Errx, ValueError, TypeError):
    """EX_DATAERR"""
    exit_code = 65


class SoftwareError(Errx):
    """EX_SOFTWARE"""
    exit_code = EX.EX_SOFTWARE


class ProtocolError(Errx):
    """
    EX_PROTOCOL
    FIXME:
        maybe IOError + EX.EX_PROTOCOL = 74
        maybe OSError + EX.EX_PROTOCOL = 3
    """
    exit_code = 76


class _IOError(Errx, IOError):
    """EX_IOERR"""
    exit_code = 74


class NoInputError(Errx, OSError):
    """EX_NOINPUT"""
    exit_code = 66  # FileNotFoundError + EX.EX_NOINPUT


class UsbIOError(Errx, IOError):
    """USB IOError"""
    exit_code = 1  # FIXME: maybe IOError + EX.EX_IOERR = 74


class MissUseError(Errx):
    """
    Often used to indicate misuse or incorrect usage of the program.
    For example, if the program receives
    invalid command-line arguments or options,
    it might exit with code 2 to indicate a syntax error.
    """
    exit_code = 2   # FIXME: maybe SystemExit + EX.EX_USAGE = 1


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
    'UsbIOError',
    'MissUseError',
    'SoftwareError',
    'ProtocolError',
    'CompatibilityError',
    'DataError',
    'UsbIOError',
    '_IOError',
    'except_and_safe_exit'
)


import errno

# def handle_error(exception):
#     error_code = getattr(errno, exception.__class__.__name__, 1)
#     print(f"Error: {exception.__class__.__name__}, exit code: {error_code}")
#     exit(error_code)
#
# try:
#     # Code that may raise exceptions
#     # Example:
#     # 1 / 0  # This would raise a ZeroDivisionError
#     raise FileNotFoundError("File not found")
# except Exception as e:
#     handle_error(e)

# print(errno.__dict__)

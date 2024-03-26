"""
Default logger initializer for pydfuutil
"""

import logging

__all__ = ('get_logger', )


def get_logger(name: str = "default"):
    """get_logger with specified defaults"""

    formatter = logging.Formatter('%(levelname)s %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(stream_handler)
    return logger

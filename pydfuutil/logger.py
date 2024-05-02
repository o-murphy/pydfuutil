"""
Default logger initializer for pydfuutil
"""

import logging

__all__ = ('logger', )


formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger('pydfuutil')
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)

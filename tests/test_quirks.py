import logging
import unittest
from pydfuutil.quirks import *
from pydfuutil.logger import logger

logger.setLevel(logging.DEBUG)


class TestSetQuirks(unittest.TestCase):

    def test_quirk_polltimeout(self):
        self.assertEqual(get_quirks(VENDOR.OPENMOKO, PRODUCT.FREERUNNER_FIRST , 1), QUIRK.POLLTIMEOUT)
        self.assertEqual(get_quirks(VENDOR.FIC, PRODUCT.FREERUNNER_LAST, 1), QUIRK.POLLTIMEOUT)
        self.assertEqual(get_quirks(VENDOR.VOTI, PRODUCT.OPENPCD, 1), QUIRK.POLLTIMEOUT)

    def test_quirk_force_dfu11(self):
        self.assertEqual(get_quirks(VENDOR.LEAFLABS, PRODUCT.MAPLE3, 0x0200), QUIRK.FORCE_DFU11)
        self.assertEqual(get_quirks(VENDOR.LEAFLABS, PRODUCT.MAPLE3, 0x0100), 0)
        self.assertEqual(get_quirks(VENDOR.LEAFLABS, PRODUCT.MAPLE3, 0x0200), QUIRK.FORCE_DFU11)
        self.assertEqual(get_quirks(VENDOR.LEAFLABS, PRODUCT.MAPLE3, 0x0300), 0)

if __name__ == '__main__':
    unittest.main()

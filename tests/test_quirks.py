import logging
import unittest
from pydfuutil.quirks import *
from pydfuutil.logger import logger

logger.setLevel(logging.DEBUG)


class TestSetQuirks(unittest.TestCase):

    def test_quirk_polltimeout(self):
        self.assertEqual(set_quirks(VENDOR_OPENMOKO, 123, 1), QUIRK_POLLTIMEOUT)
        self.assertEqual(set_quirks(VENDOR_FIC, 456, 1), QUIRK_POLLTIMEOUT)
        self.assertEqual(set_quirks(VENDOR_VOTI, 789, 1), QUIRK_POLLTIMEOUT)

    def test_quirk_force_dfu11(self):
        self.assertEqual(set_quirks(VENDOR_LEAFLABS, PRODUCT_MAPLE3, 0x0200), QUIRK_FORCE_DFU11)
        self.assertEqual(set_quirks(VENDOR_LEAFLABS, PRODUCT_MAPLE3, 0x0100), 0)
        self.assertEqual(set_quirks(VENDOR_LEAFLABS, 123, 0x0200), 0)
        self.assertEqual(set_quirks(VENDOR_LEAFLABS, PRODUCT_MAPLE3, 0x0300), 0)

if __name__ == '__main__':
    unittest.main()

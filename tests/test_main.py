import unittest
from pydfuutil.__main__ import *


class TestMain(unittest.TestCase):

    def test_usb_path2devnum(self):
        ret = usb_path2devnum('1-0.8:1.0')
        self.assertEqual(ret, 8)


if __name__ == '__main__':
    unittest.main()

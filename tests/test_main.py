import unittest
from pydfuutil.__main__ import *


class TestMain(unittest.TestCase):

    def test_usb_path2devnum(self):
        ret = usb_path2devnum('1-0.8:1.0')
        self.assertEqual(ret, 8)

    def test_get_first_in_gen(self):

        def gen():
            for i in range(5, 10):
                yield None
                yield i

        def gen2():
            for i in range(5, 10):
                yield None


        v = next((v for v in gen() if v is not None), None)
        v2 = next((v2 for v2 in gen2() if v2 is not None), None)
        self.assertEqual(v, 5)
        self.assertEqual(v2, None)


if __name__ == '__main__':
    unittest.main()

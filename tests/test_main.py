import unittest
from pydfuutil.__main__ import *


class TestMain(unittest.TestCase):

    @unittest.skip("Already implemented")
    def test_find_dfu_if_first(self):
        ctx = usb.core.find(find_all=True)
        for dev in ctx:
            dfu_if = next((i for i in find_dfu_if(dev) if i is not None), None)
            if dfu_if:
                print_dfu_if(dfu_if)

    @unittest.skip("Already implemented")
    def test_get_first_dfu_if(self):
        dev = usb.core.find(idVendor=0x1fc9, idProduct=0x000c)
        if dfu_if := get_first_dfu_if(dev):
            print_dfu_if(dfu_if)


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

    @unittest.skip("Already implemented")
    def test_main_upload(self):
        argv = "-U test.bin -t 2048 -y".split(' ')
        main(argv)


if __name__ == '__main__':
    unittest.main()

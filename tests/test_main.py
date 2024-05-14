import unittest
from pydfuutil.__main__ import *


class TestMain(unittest.TestCase):

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

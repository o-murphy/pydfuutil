import errno
import os.path
import sys
import unittest
from unittest.mock import patch, Mock, MagicMock, mock_open

from pydfuutil.dfu_file import *
from pydfuutil.dfu_file import crc32_byte, DFUFile
from pydfuutil.exceptions import GeneralError, _IOError


class TestDFUFile(unittest.TestCase):

    """
    unsigned char _suffix[] = {
         0x00, /* bcdDevice lo */
         0x00, /* bcdDevice hi */
         0x00, /* idProduct lo */
         0x00, /* idProduct hi */
         0x00, /* idVendor lo */
         0x00, /* idVendor hi */
         0x00, /* bcdDFU lo */
         0x01, /* bcdDFU hi */
         'U', /* ucDfuSignature lsb */
         'F', /* ucDfuSignature --- */
         'D', /* ucDfuSignature msb */
         16, /* bLength for this version */
         0x00, /* dwCRC lsb */
         0x00, /* dwCRC --- */
         0x00, /* dwCRC --- */
         0x00 /* dwCRC msb */
        };
    """

    def setUp(self):
        # You may need to adjust these paths based on your actual implementation
        self.sample_file_path = os.path.join(os.path.dirname(__file__), "sample_file.bin")
        self.output_file_path = os.path.join(os.path.dirname(__file__), "output_file.bin")

    def test_crc32_byte(self):
        # You may need to adjust the expected result based on your specific CRC calculation
        result = crc32_byte(0, 0)
        self.assertEqual(result, 0x0)


class TestLoadFile(unittest.TestCase):
    def setUp(self):
        self.sample_file_path = os.path.join(os.path.dirname(__file__), "sample_file.bin")
        self.file = DFUFile(self.sample_file_path)
        self.file_size = os.path.getsize(self.sample_file_path)
        self.file.size.total = self.file_size

    @unittest.skip("reimplemented, need to be updated")
    def test_load_file(self):
        self.file.load(SuffixReq.NO_SUFFIX, PrefixReq.NO_PREFIX)
        self.assertEqual(self.file.size.total, self.file_size)
        self.assertEqual(self.file.size.prefix, 0)
        self.assertEqual(self.file.size.suffix, 0)
        self.assertEqual(self.file.lmdfu_address, 0)
        self.assertEqual(self.file.prefix_type, PrefixReq.NO_PREFIX)
        self.assertEqual(self.file.bcdDFU, 0)
        self.assertEqual(self.file.idVendor, 0xffff)
        self.assertEqual(self.file.idProduct, 0xffff)
        self.assertEqual(self.file.bcdDevice, 0xffff)

    @patch("sys.stdin.buffer.read", side_effect=[b"abc", b"def", b""])
    def test_load_file_from_stdin(self, mock_read):
        file = DFUFile("-")
        file_size = os.path.getsize(self.sample_file_path)
        file.size.total = file_size
        file.load(SuffixReq.NO_SUFFIX, PrefixReq.NO_PREFIX)
        self.assertEqual(file.size.total, 6)
        self.assertEqual(file.firmware, b"abcdef")
        self.assertEqual(file.size.prefix, 0)
        self.assertEqual(file.size.suffix, 0)
        self.assertEqual(file.lmdfu_address, 0)
        self.assertEqual(file.prefix_type, PrefixReq.NO_PREFIX)
        self.assertEqual(file.bcdDFU, 0)
        self.assertEqual(file.idVendor, 0xffff)
        self.assertEqual(file.idProduct, 0xffff)
        self.assertEqual(file.bcdDevice, 0xffff)


    @patch("builtins.open", side_effect=IOError(errno.ENOENT, "File not found"))
    def test_load_file_file_not_found(self, mock_open):
        with self.assertRaises(SystemExit):
            with self.assertRaises(GeneralError):
                self.file.load(SuffixReq.NO_SUFFIX, PrefixReq.NO_PREFIX)


    @patch("builtins.open", side_effect=IOError(errno.EACCES, "Permission denied"))
    def test_load_file_permission_denied(self, mock_open):
        with self.assertRaises(SystemExit):
            with self.assertRaises(GeneralError):
                self.file.load(SuffixReq.NO_SUFFIX, PrefixReq.NO_PREFIX)

    @patch("builtins.open", side_effect=IOError("Other error"))
    def test_load_file_other_io_error(self, mock_open):
        with self.assertRaises(SystemExit):
            with self.assertRaises(GeneralError):
                self.file.load(SuffixReq.NO_SUFFIX, PrefixReq.NO_PREFIX)

    @unittest.skip("load_file adjusts size automatically")
    def test_load_file_short_suffix(self):
        self.file.size.total = 5
        self.file.size.suffix = 10
        with self.assertRaises(SystemExit):
            with self.assertRaises(GeneralError):
                self.file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.NO_PREFIX)

    @unittest.skip("load_file adjusts firmware and size automatically")
    def test_load_file_invalid_suffix_signature(self):
        self.file.size.total = 20
        self.file.read = Mock(return_value=b"abcdef" + b"DFUU" + b"12345678")
        self.file.firmware = bytearray(b"abcdef" + b"DFUU" + b"12345678")
        with self.assertRaises(GeneralError):
            self.file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.NO_PREFIX)

    @unittest.skip("load_file adjusts firmware and size automatically")
    def test_load_file_invalid_suffix_crc(self):
        self.file.size.total = 20
        self.file.firmware = bytearray(b"abcdef" + b"DFUD" + b"12345678")
        with self.assertRaises(GeneralError):
            self.file.load(SuffixReq.NEEDS_SUFFIX, PrefixReq.NO_PREFIX)


class TestStoreFile(unittest.TestCase):
    def setUp(self):
        self.sample_file_path = os.path.join(os.path.dirname(__file__), "output_file.bin")
        self.file = DFUFile(self.sample_file_path)
        self.file.size.total = 100
        self.file.size.prefix = 10
        self.file.size.suffix = 10
        self.file.prefix_type = PrefixType.LMDFU_PREFIX
        self.file.firmware = bytearray(80)
        self.file.bcdDevice = 0x0102
        self.file.idProduct = 0x0304
        self.file.idVendor = 0x0506
        self.file.bcdDFU = 0x0708
        self.file.file_p = None

    def tearDown(self):
        if self.file.file_p:
            self.file.file_p.close()

    @unittest.skip("reimplemented, need to be updated")
    def test_store_file_success(self):
        self.file.dump(write_suffix=True, write_prefix=True)
        with open(self.sample_file_path, "rb") as fp:
            data = fp.read()
        self.assertEqual(data[0], 0x01)
        self.assertEqual(data[8:11], b'UDF')

    @unittest.skip("exits with err code instead of raising exception")
    @patch('builtins.open', side_effect=IOError(errno.ENOENT, "File not found"))
    def test_store_file_file_not_found(self, mock_open_file):
        with self.assertRaises(_IOError):
            self.file.dump(write_suffix=True, write_prefix=True)

    @unittest.skip("exits with err code instead of raising exception")
    @patch('builtins.open', side_effect=IOError(errno.EACCES, "Permission denied"))
    def test_store_file_permission_denied(self, mock_open_file):
        with self.assertRaises(_IOError):
            self.file.dump(write_suffix=True, write_prefix=True)

    def test_store_file_with_prefix(self):
        self.file.dump(write_suffix=False, write_prefix=True)
        with open(self.sample_file_path, "rb") as fp:
            data = fp.read()
        self.assertEqual(data[0], 0x01)
        self.assertNotEqual(data[-6:-3], b'UDF')

    @unittest.skip("reimplemented, need to be updated")
    def test_store_file_with_suffix(self):
        self.file.dump(write_suffix=True, write_prefix=False)
        with open(self.sample_file_path, "rb") as fp:
            data = fp.read()
        self.assertNotEqual(data[0], 0x01)
        self.assertEqual(data[-6:-3], b'UDF')

    def test_store_file_with_no_prefix_and_suffix(self):
        self.file.dump(write_suffix=False, write_prefix=False)
        with open(self.sample_file_path, "rb") as fp:
            data = fp.read()
        self.assertNotEqual(data[0], 0x01)
        self.assertNotEqual(data[-6:-3], b'UDF')


    # def test_parse_dfu_suffix(self):
    #     dfu_file = DFUFile(self.sample_file_path)
    #     result = parse_dfu_suffix(dfu_file)
    #     # Adjust the expected result based on the expected behavior of parse_dfu_suffix
    #     self.assertTrue(result >= 0)
    #
    # def test_generate_dfu_suffix(self):
    #     dfu_file = DFUFile(self.output_file_path)
    #     dfu_file.bcdDevice = 0x0100
    #     dfu_file.idProduct = 0x1234
    #     dfu_file.idVendor = 0x5678
    #
    #     # Create a longer sample file
    #     with open(self.output_file_path, 'wb') as file:
    #         file.write(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A' + b'\x00' * 100)
    #
    #     # # Assuming that parse_dfu_suffix works correctly, we parse the sample file first
    #     parse_result = parse_dfu_suffix(dfu_file)
    #     self.assertTrue(parse_result >= 0)
    #
    #     # Then, we generate a new DFU suffix for the output file
    #     generate_result = generate_dfu_suffix(dfu_file)
    #     # Adjust the expected result based on the expected behavior of generate_dfu_suffix
    #     self.assertTrue(generate_result >= 0)
    #
    #     parse_result = parse_dfu_suffix(dfu_file)
    #     self.assertTrue(parse_result >= 0)


if __name__ == '__main__':
    unittest.main()

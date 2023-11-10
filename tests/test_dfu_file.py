import unittest

from pydfuutil.dfu_file import *


class TestDFUFunctions(unittest.TestCase):

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

    # valid_dfu_suffix = (
    #         b'\x00' * 10 +  # Padding bytes
    #         b'DFU' +  # Signature ('DFU') reversed for big-endian
    #         b'\x01\x00' +  # bcdDFU version (e.g., 1.0)
    #         b'\x08' +  # Length of the suffix (e.g., 8 bytes)
    #         b'\x34\x12' +  # idProduct (16-bit little-endian)
    #         b'\x78\x56' +  # idVendor (16-bit little-endian)
    #         b'\x00\x01' +  # bcdDevice (16-bit little-endian)
    #         b'\xFF\xFF\xFF\xFF'  # dwCRC (32-bit little-endian, often set to 0xFFFFFFFF)
    # )

    def setUp(self):
        # You may need to adjust these paths based on your actual implementation
        self.sample_file_path = "sample_file.bin"
        self.output_file_path = "output_file.bin"

    def test_crc32_byte(self):
        # You may need to adjust the expected result based on your specific CRC calculation
        result = crc32_byte(0, 0)
        self.assertEqual(result, 0x0)

    def test_parse_dfu_suffix(self):
        dfu_file = DFUFile(self.sample_file_path)
        result = parse_dfu_suffix(dfu_file)
        # Adjust the expected result based on the expected behavior of parse_dfu_suffix
        self.assertTrue(result >= 0)

    def test_generate_dfu_suffix(self):
        dfu_file = DFUFile(self.output_file_path)
        dfu_file.bcdDevice = 0x0100
        dfu_file.idProduct = 0x1234
        dfu_file.idVendor = 0x5678

        # Create a longer sample file
        with open(self.output_file_path, 'wb') as file:
            file.write(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A' + b'\x00' * 100)

        # # # Assuming that parse_dfu_suffix works correctly, we parse the sample file first
        # parse_result = parse_dfu_suffix(dfu_file)
        # self.assertTrue(parse_result >= 0)

        # Then, we generate a new DFU suffix for the output file
        generate_result = generate_dfu_suffix(dfu_file)
        # Adjust the expected result based on the expected behavior of generate_dfu_suffix
        self.assertTrue(generate_result >= 0)

        parse_result = parse_dfu_suffix(dfu_file)
        self.assertTrue(parse_result >= 0)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import Mock, patch

from pydfuutil.dfu_load import *


class TestDFULoader(unittest.TestCase):
    @patch('pydfuutil.dfu_load.dfu_upload')
    def test_dfuload_do_upload(self, mock_dfu_upload):
        dif = Mock()
        xfer_size = 256
        file = DFUFile(name='test_file')  # Provide a mock file object
        file.filep = Mock()  # Provide a mock file object
        total_size = 1024

        # Mock dfu_upload to return data
        mock_dfu_upload.return_value = b'\x00' * xfer_size

        # Mock filep.write to return the length of the data written
        with patch.object(file.filep, 'write', return_value=xfer_size) as mock_write:
            result = dfuload_do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(result, total_size)  # Assuming xfer_size bytes are received


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import Mock, patch

from pydfuutil.dfu_load import *


class TestDFULoader(unittest.TestCase):
    @patch('pydfuutil.dfu.upload')
    def test_dfuload_do_upload(self, mock_dfu_upload):
        dif = Mock()
        xfer_size = 256
        file = DFUFile(name='test_file', filep=Mock())  # Provide a mock file object
        total_size = 1024

        # Mock dfu_upload to return data
        mock_dfu_upload.return_value = b'\x00' * xfer_size

        # Mock filep.write to return the length of the data written
        with patch.object(file.filep, 'write', return_value=xfer_size) as mock_write:
            result = do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(result, total_size)  # Assuming xfer_size bytes are received

    @patch('pydfuutil.dfu.download')  # Mock 'dfu_download'
    @patch('pydfuutil.dfu.get_status')  # Mock 'dfu_get_status'
    def test_dfuload_do_dnload(self, mock_dfu_get_status, mock_dfu_download):
        dif = Mock()
        xfer_size = 1024
        file = DFUFile(name='test_file', filep=Mock(), size=xfer_size, suffixlen=0)
        quirks = 0
        verbose = True

        result = dfu.StatusData(dfu.Status.OK, 100, dfu.State.DFU_DOWNLOAD_IDLE, 0)

        # # Mock dfu_download to return the length of the data sent
        mock_dfu_download.return_value = xfer_size

        # # Mock dfu_get_status to return a mock DFU status
        # # mock_dfu_get_status.return_value = int.from_bytes(result, byteorder='little'), status
        mock_dfu_get_status.return_value = result

        print(mock_dfu_download.return_value)

        # Mock filep.readinto to return the length of the data read
        with patch.object(file.filep, 'readinto', return_value=xfer_size) as mock_readinto:

            result = do_dnload(dif, xfer_size, file, quirks, verbose)

        # Assertions
        self.assertEqual(result, xfer_size)  # Assuming xfer_size bytes are sent


if __name__ == '__main__':
    unittest.main()

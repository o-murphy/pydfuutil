import unittest
from unittest.mock import Mock, patch

from pydfuutil import dfu
from pydfuutil.dfu_load import DFUFile, do_upload, do_dnload


class TestDFULoader(unittest.TestCase):

    def test_dfu_load_do_upload(self):
        xfer_size = 256
        file = DFUFile(name='test_file', file_p=Mock())  # Provide a mock file object
        total_size = 4096

        dif = Mock()
        dif.upload.return_value = bytes(xfer_size)
        dif.get_status.return_value = total_size

        # Mock file_p.write to return the length of the data written
        with patch.object(file.file_p, 'write', return_value=xfer_size) as mock_write:
            result = do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(result, total_size)  # Assuming total_size bytes are received

    def test_dfu_load_do_dnload(self):

        xfer_size = 1024
        result = dfu.StatusRetVal(dfu.Status.OK, 100, dfu.State.DFU_DOWNLOAD_IDLE, 0)

        dif = Mock()
        dif.download.return_value = xfer_size
        dif.get_status.return_value = result

        file = DFUFile(name='test_file', file_p=Mock(), size=xfer_size, suffix_len=0)
        quirks = 0
        verbose = False

        # Mock file_p.readinto to return the length of the data read
        with patch.object(file.file_p, 'readinto', return_value=xfer_size) as mock_readinto:
            result = do_dnload(dif, xfer_size, file, quirks, verbose)

        # Assertions
        self.assertEqual(result, xfer_size)  # Assuming xfer_size bytes are sent


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import Mock, patch, MagicMock

from pydfuutil import dfu
from pydfuutil.dfu_load import DfuFile, do_upload, do_download


class TestDFULoader(unittest.TestCase):

    def test_dfu_load_do_upload(self):
        xfer_size = 256
        file = DfuFile(name='test_file', file_p=Mock())  # Provide a mock file object
        total_size = 4096

        dif = Mock()
        dif.upload.return_value = bytes(xfer_size)
        dif.get_status.return_value = total_size

        # Mock file_p.write to return the length of the data written
        with patch.object(file.file_p, 'write', return_value=xfer_size) as mock_write:
            result = do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(result, total_size)  # Assuming expected_size bytes are received

    def test_dfu_load_do_dnload(self):

        xfer_size = 1024
        result = dfu.StatusRetVal(dfu.Status.OK, 100, dfu.State.DFU_DOWNLOAD_IDLE, 0)

        dif = Mock(spec_set=dfu.DfuIf)
        dif.download.return_value = xfer_size
        dif.get_status.return_value = result

        file = DfuFile(name='test_file', file_p=Mock())
        file.size.total = xfer_size * 10
        file.size.suffix = 0
        dif.quirks = 0

        # Mock file_p.readinto to return the length of the data read
        with patch.object(file.file_p, 'readinto', return_value=xfer_size) as mock_readinto:
            result = do_download(dif, xfer_size, file)

        # Assertions
        self.assertEqual(result, file.size.total)  # Assuming xfer_size bytes are sent


if __name__ == '__main__':
    unittest.main()

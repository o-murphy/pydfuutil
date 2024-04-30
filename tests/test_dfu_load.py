import unittest
from unittest.mock import Mock, patch

from pydfuutil.dfu_load import *


class TestDFULoader(unittest.TestCase):

    def test_dfuload_do_upload(self):
        xfer_size = 256
        file = DFUFile(name='test_file', filep=Mock())  # Provide a mock file object
        total_size = 1024

        dif = Mock()
        dif.upload.return_value = bytes(xfer_size)
        dif.get_status.return_value = total_size

        # Mock filep.write to return the length of the data written
        with patch.object(file.filep, 'write', return_value=xfer_size) as mock_write:
            result = do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(result, total_size)  # Assuming total_size bytes are received

    def test_dfuload_do_dnload(self):

        xfer_size = 1024
        result = dfu.StatusData(dfu.Status.OK, 100, dfu.State.DFU_DOWNLOAD_IDLE, 0)

        dif = Mock()
        dif.download.return_value = xfer_size
        dif.get_status.return_value = result

        file = DFUFile(name='test_file', filep=Mock(), size=xfer_size, suffixlen=0)
        quirks = 0
        verbose = True

        # Mock filep.readinto to return the length of the data read
        with patch.object(file.filep, 'readinto', return_value=xfer_size) as mock_readinto:
            result = do_dnload(dif, xfer_size, file, quirks, verbose)

        # Assertions
        self.assertEqual(result, xfer_size)  # Assuming xfer_size bytes are sent


if __name__ == '__main__':
    unittest.main()

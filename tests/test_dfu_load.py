import unittest
from unittest.mock import Mock, patch

from pydfuutil import dfu
from pydfuutil.dfu_load import DfuFile, do_upload, do_download


class TestDFULoader(unittest.TestCase):
    def test_dfu_load_do_upload(self):
        xfer_size = 256
        file = DfuFile(name="test_file", file_p=Mock())  # Provide a mock file object
        total_size = 4096
        num_full_chunks = total_size // xfer_size

        dif = Mock()
        # a real device signals completion with a short (here: empty) final block;
        # the loop must terminate on that alone, not on reaching expected_size
        dif.upload.side_effect = [bytes(xfer_size)] * num_full_chunks + [b""]
        dif.get_status.return_value = total_size

        # Mock file_p.write to return the length of whatever was actually written
        with patch.object(file.file_p, "write", side_effect=len):
            result = do_upload(dif, xfer_size, file, total_size)

        # Assertions
        self.assertEqual(
            result, total_size
        )  # Assuming expected_size bytes are received

    def test_dfu_load_do_dnload(self):

        xfer_size = 1024
        total_size = xfer_size * 10
        status = dfu.StatusRetVal(dfu.Status.OK, 0, dfu.State.DFU_DOWNLOAD_IDLE, 0)
        final_status = dfu.StatusRetVal(dfu.Status.OK, 0, dfu.State.DFU_IDLE, 0)

        dif = Mock(spec_set=dfu.DfuIf)
        dif.download.return_value = xfer_size
        # one status per chunk (10 chunks) + one final "transition to manifest" status
        dif.get_status.side_effect = [status] * 10 + [final_status]

        file = DfuFile(name="test_file", firmware=bytes(total_size))
        file.size.total = total_size
        file.size.suffix = 0
        dif.quirks = 0

        result = do_download(dif, xfer_size, file)

        # Assertions
        self.assertEqual(result, file.size.total)  # Assuming xfer_size bytes are sent
        # transaction must increment per chunk, plus final zero-length completion packet
        transactions = [call.args[0] for call in dif.download.call_args_list]
        self.assertEqual(transactions, list(range(11)))


if __name__ == "__main__":
    unittest.main()

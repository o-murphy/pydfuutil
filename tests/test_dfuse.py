import unittest
from unittest.mock import Mock, patch

import usb.util

from pydfuutil import dfuse, dfu, dfuse_mem
from pydfuutil.dfu_file import DFUFile
from pydfuutil.dfuse_mem import parse_memory_layout


class TestSpecialCommand(unittest.TestCase):

    def setUp(self):
        dfuse.MEM_LAYOUT = parse_memory_layout(
            "@Internal Flash/0x08000000/04*016Kg,01*064Kg,01*128Kg"
        )
        self.dfu_if = Mock()
        self.dfu_if.abort.return_value = 0
        self.dfu_if.dev.ctrl_transfer.return_value = 0
        self.dfu_if.get_status.side_effect = [
            dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_BUSY, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
        ]
        self.address = 0x8000000

    def test_erase_page_command(self):
        ret = dfuse.special_command(self.dfu_if, self.address, dfuse.Command.ERASE_PAGE)
        self.assertGreater(ret, 0)

    def test_set_address_command(self):
        ret = dfuse.special_command(self.dfu_if, self.address, dfuse.Command.SET_ADDRESS)
        self.assertGreater(ret, 1)

    def test_mass_erase_command(self):
        ret = dfuse.special_command(self.dfu_if, self.address, dfuse.Command.MASS_ERASE)
        self.assertGreater(ret, 1)

    def test_read_unprotect_command(self):
        ret = dfuse.special_command(self.dfu_if, self.address, dfuse.Command.READ_UNPROTECT)
        self.assertGreater(ret, 1)


class TestUpload(unittest.TestCase):

    def setUp(self):
        dfu.init(5000)
        self.dfu_if = Mock()

    def test_upload_success(self):
        self.dfu_if.dev.ctrl_transfer.return_value = 1
        data = b'\x01\x02\x03\x04'
        transaction = 123
        status = dfuse.upload(self.dfu_if, data, transaction)
        self.assertEqual(status, 1)
        self.dfu_if.dev.ctrl_transfer.assert_called_once_with(
            bmRequestType=usb.util.ENDPOINT_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
            bRequest=dfu.Command.UPLOAD,
            wValue=transaction,
            wIndex=self.dfu_if.interface,
            data_or_wLength=data,
            timeout=dfu.TIMEOUT
        )

    def test_upload_failure(self):
        self.dfu_if.dev.ctrl_transfer.return_value = -1
        data = b'\x01\x02\x03\x04'
        transaction = 123
        status = dfuse.upload(self.dfu_if, data, transaction)
        self.assertEqual(status, -1)
        self.dfu_if.dev.ctrl_transfer.assert_called_once()


class TestDownload(unittest.TestCase):

    def setUp(self):
        dfu.init(5000)
        self.dfu_if = Mock()

    def test_download_success(self):
        self.dfu_if.dev.ctrl_transfer.return_value = 1
        data = b'\x01\x02\x03\x04'
        transaction = 123
        status = dfuse.download(self.dfu_if, data, transaction)
        self.assertEqual(status, 1)
        self.dfu_if.dev.ctrl_transfer.assert_called_once_with(
            bmRequestType=usb.util.ENDPOINT_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
            bRequest=dfu.Command.DNLOAD,
            wValue=transaction,
            wIndex=self.dfu_if.interface,
            data_or_wLength=data,
            timeout=dfu.TIMEOUT
        )

    def test_download_failure(self):
        self.dfu_if.dev.ctrl_transfer.return_value = -1
        data = b'\x01\x02\x03\x04'
        transaction = 123
        status = dfuse.download(self.dfu_if, data, transaction)
        self.assertEqual(status, -1)
        self.dfu_if.dev.ctrl_transfer.assert_called_once()


class TestDnloadChunk(unittest.TestCase):
    def setUp(self):
        dfu.init(5000)
        self.dfu_if = Mock()

    @patch('pydfuutil.dfuse.download')
    def test_dnload_chunk_success(self, mock_download):
        mock_download.return_value = 4
        status_mock = dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_IDLE, bStatus=dfu.Status.OK)
        self.dfu_if.get_status.return_value = status_mock
        data = b'\x01\x02\x03\x04'
        size = len(data)
        transaction = 123
        bytes_sent = dfuse.dnload_chunk(self.dfu_if, data, size, transaction)
        self.assertEqual(bytes_sent, 4)
        mock_download.assert_called_once_with(self.dfu_if, data, transaction)
        self.assertEqual(self.dfu_if.get_status.call_count, 1)

    @patch('pydfuutil.dfuse.download')
    def test_dnload_chunk_failure(self, mock_download):
        mock_download.return_value = -1
        data = b'\x01\x02\x03\x04'
        size = len(data)
        transaction = 123
        bytes_sent = dfuse.dnload_chunk(self.dfu_if, data, size, transaction)
        self.assertEqual(bytes_sent, -1)
        mock_download.assert_called_once_with(self.dfu_if, data, transaction)
        self.assertEqual(self.dfu_if.get_status.call_count, 0)


class TestDoUpload(unittest.TestCase):

    def setUp(self):
        self.dfu_if = Mock()
        self.dfu_if.abort.return_value = 0
        self.dfu_if.alt_name = "@Internal Flash/0x08000000/04*016Kg,01*064Kg,01*128Kg"
        self.dfu_if.dev.ctrl_transfer.return_value = 0
        self.dfu_if.get_status.side_effect = [
            dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_BUSY, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
        ]
        self.dfuse_options = "--address 0x08000000"
        self.file = DFUFile("")
        self.file.file_p = Mock()
        self.chunk_sizes = [
            1024, 512, 256
        ]
        self.file.file_p.write.side_effect = self.chunk_sizes
        self.xfer_size = sum(self.chunk_sizes)

    @patch('pydfuutil.dfuse.parse_options')
    @patch('pydfuutil.dfuse.upload')
    def test_do_upload_with_options_and_address(self, mock_upload, mock_parse_options):
        mock_parse_options.return_value = Mock(address=0x08000000, length=0x4000, force=False)
        mock_upload.side_effect = self.chunk_sizes
        self.assertEqual(dfuse.do_upload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), 1024)

    @patch('pydfuutil.dfuse.parse_options')
    @patch('pydfuutil.dfuse.upload')
    def test_do_upload_with_options_and_no_address(self, mock_upload, mock_parse_options):
        mock_parse_options.return_value = Mock(address=None, length=0x4000, force=False)
        mock_upload.side_effect = self.chunk_sizes
        self.assertEqual(dfuse.do_upload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), 1024)

    @patch('pydfuutil.dfuse.parse_options')
    def test_do_upload_no_options(self, mock_parse_options):
        mock_parse_options.side_effect = ValueError("No options provided")
        self.assertEqual(dfuse.do_upload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), -1)

class TestDnloadElement(unittest.TestCase):

    def setUp(self):
        dfuse.MEM_LAYOUT = parse_memory_layout(
            "@Internal Flash/0x08000000/04*016Kg,01*064Kg,01*128Kg"
        )
        dfu.init(5000)
        self.dfu_if = Mock()
        self.dfu_if.abort.return_value = 0
        self.dfu_if.dev.ctrl_transfer.return_value = 0

        self.dw_element_address = 0x08000000
        self.dw_element_size = 1024
        self.data = b'\x01\x02\x03\x04'
        self.xfer_size = 512

        self.dfu_if.get_status.side_effect = [
            dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_BUSY, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
        ] * (self.dw_element_size // self.xfer_size)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_success(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = Mock(mem_type=dfuse_mem.DFUSE.WRITEABLE)
        mock_dnload_chunk.return_value = 512
        self.assertEqual(dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size), 512)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_segment_not_found(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = None
        mock_dnload_chunk.return_value = -1
        self.assertEqual(dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size), -1)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_segment_not_writeable(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = Mock(mem_type=0)
        mock_dnload_chunk.return_value = -1
        self.assertEqual(dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size), -1)


if __name__ == '__main__':
    unittest.main()

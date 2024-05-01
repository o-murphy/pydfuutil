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
                                                 dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_BUSY,
                                                                  bStatus=dfu.Status.OK),
                                                 dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
                                                 dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
                                             ] * (self.dw_element_size // self.xfer_size)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_success(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = Mock(mem_type=dfuse_mem.DFUSE.WRITEABLE)
        mock_dnload_chunk.return_value = 512
        self.assertEqual(
            dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size),
            512)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_segment_not_found(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = None
        mock_dnload_chunk.return_value = -1
        self.assertEqual(
            dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size),
            -1)

    @patch('pydfuutil.dfuse_mem.find_segment')
    @patch('pydfuutil.dfuse.dnload_chunk')
    def test_dnload_element_segment_not_writeable(self, mock_dnload_chunk, mock_find_segment):
        mock_find_segment.return_value = Mock(mem_type=0)
        mock_dnload_chunk.return_value = -1
        self.assertEqual(
            dfuse.dnload_element(self.dfu_if, self.dw_element_address, self.dw_element_size, self.data, self.xfer_size),
            -1)


class TestDoBinDnload(unittest.TestCase):

    def setUp(self):
        self.dfu_if = Mock()
        self.xfer_size = 1024
        self.start_address = 0x08000000
        self.file = Mock(spec=DFUFile)
        self.file.size = 1024
        self.file.file_p.read.return_value = bytes(1024)

    @patch('pydfuutil.dfuse.dnload_element')
    def test_do_bin_dnload_success(self, mock_dnload_element):
        mock_dnload_element.return_value = 0
        self.assertEqual(dfuse.do_bin_dnload(self.dfu_if, self.xfer_size, self.file, self.start_address),
                         self.file.size)

    @patch('pydfuutil.dfuse.dnload_element')
    def test_do_bin_dnload_failure(self, mock_dnload_element):
        mock_dnload_element.return_value = -1
        self.assertEqual(dfuse.do_bin_dnload(self.dfu_if, self.xfer_size, self.file, self.start_address), -1)


class TestDoDfuseDnload(unittest.TestCase):

    def setUp(self):
        self.dfu_if = Mock()
        self.xfer_size = 1024
        self.file = DFUFile("")
        self.file.file_p = Mock()
        self.file.suffix_len = 16

    @patch('pydfuutil.dfuse.dnload_element')
    def test_do_dfuse_dnload_success(self, mock_dnload_element):
        mock_dnload_element.return_value = 0
        # self.file.file_p.read.return_value = b'DfuSe\x01\x01Target\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        read_values = [
            b'DfuSe\x01\x01\x00\x00\x00\x00',
            bytes(16),
        ]
        self.file.file_p.read.side_effect = read_values
        self.file.size = 11 + 16
        self.assertEqual(dfuse.do_dfuse_dnload(self.dfu_if, self.xfer_size, self.file), self.file.size)

    def test_do_dfuse_dnload_invalid_signature(self):
        self.file.file_p.read.return_value = b'InvalidSignature'
        self.assertEqual(dfuse.do_dfuse_dnload(self.dfu_if, self.xfer_size, self.file), -22)  # -errno.EINVAL

    def test_do_dfuse_dnload_invalid_target_signature(self):
        self.file.file_p.read.return_value = b'DfuSe\x01\x00InvalidTrgt'
        self.assertEqual(dfuse.do_dfuse_dnload(self.dfu_if, self.xfer_size, self.file), -22)  # -errno.EINVAL


class TestDoDnload(unittest.TestCase):

    def setUp(self):
        self.dfu_if = Mock()
        self.dfu_if.alt_name = "@Internal Flash/0x08000000/04*016Kg,01*064Kg,01*128Kg"
        self.dfu_if.dev.ctrl_transfer.return_value = 0
        self.dfu_if.get_status.side_effect = (
            dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_BUSY, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_DOWNLOAD_IDLE, bStatus=dfu.Status.OK),
            dfu.StatusRetVal(bState=dfu.State.DFU_IDLE, bStatus=dfu.Status.OK),
        )
        self.xfer_size = 1024
        self.file = DFUFile("")
        self.file.file_p = Mock()
        self.file.file_p.read.side_effect = [bytes(1024), b'']
        # self.file.bcdDFU = 0x11a
        self.file.bcdDFU = 0x0100
        self.dfuse_options = ['--dfuse-address', b'\x00\x00\x00\x00']

    @patch('pydfuutil.dfuse.do_bin_dnload')
    @patch('pydfuutil.dfuse.parse_memory_layout')
    @patch('pydfuutil.dfuse.parse_options')
    def test_do_dnload_binary(self, mock_parse_options, mock_parse_memory_layout, mock_do_bin_dnload):
        mock_parse_options.return_value = Mock(address=0x1000, unprotect=False, mass_erase=False, leave=False)
        mock_do_bin_dnload.return_value = 1024
        self.assertEqual(dfuse.do_dnload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), 1024)
        mock_do_bin_dnload.assert_called_once_with(self.dfu_if, self.xfer_size, self.file, 0x1000)

    @patch('pydfuutil.dfuse.do_dfuse_dnload')
    @patch('pydfuutil.dfuse.parse_options')
    def test_do_dnload_dfuse(self, mock_parse_options, mock_do_dfuse_dnload):
        self.file.bcdDFU = 0x11a
        opts = Mock(address=0x08000000, force=True,
                    unprotect=None, mass_erase=False)
        mock_parse_options.return_value = opts
        mock_do_dfuse_dnload.return_value = 1024
        self.assertEqual(dfuse.do_dfuse_dnload(self.dfu_if, self.xfer_size, self.file), 1024)
        mock_do_dfuse_dnload.assert_called_once_with(self.dfu_if, self.xfer_size, self.file)

    @patch('pydfuutil.dfuse.parse_options')
    def test_do_dnload_invalid_binary(self, mock_parse_options):
        self.file.bcdDFU = 0x100
        self.file.file_p.read.return_value = bytes(20)
        opts = Mock(address=0x08000000, force=True,
                    unprotect=None, mass_erase=False)
        mock_parse_options.return_value = opts
        self.assertEqual(dfuse.do_dnload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), -1)

    @patch('pydfuutil.dfuse.parse_options')
    def test_do_dnload_invalid_dfuse(self, mock_parse_options):
        self.file.bcdDFU = 0x0100
        self.file.file_p.read.return_value = bytes(20)
        opts = Mock(address=0x08000000, force=True,
                    unprotect=None, mass_erase=False)
        mock_parse_options.return_value = opts
        self.assertEqual(dfuse.do_dnload(self.dfu_if, self.xfer_size, self.file, self.dfuse_options), -1)


if __name__ == '__main__':
    unittest.main()

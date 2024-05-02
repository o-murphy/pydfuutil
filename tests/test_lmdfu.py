import logging
import unittest
from unittest.mock import MagicMock, patch
from pydfuutil.lmdfu import DFUFile, add_prefix, remove_prefix, check_prefix
from pydfuutil.logger import logger

logger.setLevel(logging.DEBUG)


class TestLmdfu(unittest.TestCase):
    @patch('pydfuutil.lmdfu.open')
    def test_add_prefix_success(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.tell.return_value = 100
        mock_open.return_value.__enter__.return_value = file_mock

        address = 0x1000
        result = add_prefix(file_mock, address)

        file_mock.file_p.write.assert_called()
        self.assertEqual(result, 0)

    @patch('pydfuutil.lmdfu.open')
    def test_add_prefix_error(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.tell.side_effect = Exception("File error")
        mock_open.return_value.__enter__.return_value = file_mock

        address = 0x1000
        result = add_prefix(file_mock, address)

        file_mock.file_p.write.assert_not_called()
        self.assertEqual(result, -1)

    @patch('pydfuutil.lmdfu.open')
    def test_remove_prefix_success(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.tell.return_value = 20
        mock_open.return_value.__enter__.return_value = file_mock

        # Mock file content
        file_content = b'TI Stellaris DFU prefix data' + b'file content'
        file_mock.file_p.read.return_value = file_content

        result = remove_prefix(file_mock)

        file_mock.file_p.truncate.assert_called_with(0)
        file_mock.file_p.write.assert_called_with(file_content[16:])
        self.assertEqual(result, 0)

    @patch('pydfuutil.lmdfu.open')
    def test_remove_prefix_error_invalid_prefix(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.tell.return_value = 10
        mock_open.return_value.__enter__.return_value = file_mock

        result = remove_prefix(file_mock)

        file_mock.file_p.truncate.assert_not_called()
        file_mock.file_p.write.assert_not_called()
        self.assertEqual(result, -1)

    @patch('pydfuutil.lmdfu.open')
    def test_remove_prefix_error_exception(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.tell.side_effect = Exception("File error")
        mock_open.return_value.__enter__.return_value = file_mock

        result = remove_prefix(file_mock)

        file_mock.file_p.truncate.assert_not_called()
        file_mock.file_p.write.assert_not_called()
        self.assertEqual(result, -1)

    @patch('pydfuutil.lmdfu.open')
    def test_check_prefix_valid(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.readinto.return_value = 16
        mock_open.return_value.__enter__.return_value = file_mock

        result = check_prefix(file_mock)

        self.assertEqual(result, 0)

    @patch('pydfuutil.lmdfu.open')
    def test_check_prefix_invalid(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.readinto.return_value = 16
        mock_open.return_value.__enter__.return_value = file_mock

        result = check_prefix(file_mock)

        self.assertEqual(result, 0)

    @patch('pydfuutil.lmdfu.open')
    def test_check_prefix_error_read(self, mock_open):
        # Mock file
        file_mock = DFUFile("")
        file_mock.file_p = MagicMock()
        file_mock.file_p.readinto.side_effect = Exception("File error")
        mock_open.return_value.__enter__.return_value = file_mock

        result = check_prefix(file_mock)

        self.assertEqual(result, -1)

if __name__ == '__main__':
    unittest.main()
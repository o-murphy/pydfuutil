import unittest
from pydfuutil import dfu
from unittest.mock import patch, MagicMock
import array


class TestDfu(unittest.TestCase):

    def setUp(self):
        dfu.init(1000)

    def test_init(self):
        self.assertEqual(dfu.TIMEOUT, 1000)

    def test_str(self):
        self.assertEqual(dfu.status_to_string(dfu.Status.OK), "No error condition is present")
        self.assertEqual(dfu.Status.OK.to_string(), "No error condition is present")
        self.assertEqual(dfu.state_to_string(dfu.State.APP_IDLE), "appIDLE")
        self.assertEqual(dfu.State.APP_IDLE.to_string(), "appIDLE")

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_detach(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 1

        # Calling the function
        interface = 0
        timeout = 1000
        result = dfu.detach(mock_device, interface, timeout)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21 | 0x01,
            bRequest=dfu.Command.DETACH,  # Assuming Command.DETACH is 23
            wValue=timeout,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 1)  # Assuming success returns 1

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_upload(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = array.array('B', [0] * 10)

        # Calling the function
        interface = 0
        transaction = 0
        data = bytes(10)
        result = dfu.upload(mock_device, interface, transaction, data)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0xa1,
            bRequest=dfu.Command.UPLOAD,  # Assuming Command.UPLOAD
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=data,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, data)  # Assuming success returns bytes(10)

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_dwnload(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 10

        # Calling the function
        interface = 0
        transaction = 0
        data = bytes(10)
        result = dfu.download(mock_device, interface, transaction, data)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Command.DNLOAD,  # Assuming Command.DNLOAD
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=data,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, len(data))  # Assuming success returns 10

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_get_status(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = array.array('B', [0] * 6)

        # Calling the function
        interface = 0
        transaction = 0
        length = 6
        status = dfu.get_status(mock_device, interface)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0xa1,
            bRequest=dfu.Command.GETSTATUS,  # Assuming Command.GETSTATUS
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=length,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(status.bState, 0)  # Assuming success returns 0

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_clear_status(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 0

        # Calling the function
        interface = 0
        transaction = 0
        result = dfu.clear_status(mock_device, interface)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Command.CLRSTATUS,  # Assuming Command.CLRSTATUS
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 0)  # Assuming success returns 0

    @patch("pydfuutil.dfu.verify_init")
    @patch("usb.core.find")
    def test_abort(self, mock_find, mock_verify_init):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 0

        # Calling the function
        interface = 0
        transaction = 0
        result = dfu.abort(mock_device, interface)

        # Assertions
        mock_verify_init.assert_called_once()
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Command.ABORT,  # Assuming Command.ABORT
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 0)  # Assuming success returns 0


if __name__ == "__main__":
    unittest.main()
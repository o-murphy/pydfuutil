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
        self.assertEqual(dfu._status_to_string(dfu.Status.OK), "No error condition is present")
        self.assertEqual(dfu.Status.OK.to_string(), "No error condition is present")
        self.assertEqual(dfu._state_to_string(dfu.State.APP_IDLE), "appIDLE")
        self.assertEqual(dfu.State.APP_IDLE.to_string(), "appIDLE")

    @patch("usb.core.find")
    def test_detach(self, mock_find):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 1

        # Calling the function
        interface = 0
        timeout = 1000
        result = dfu._detach(mock_device, interface, timeout)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21 | 0x01,
            bRequest=dfu.Request.DETACH,  # Assuming Request.DETACH is 23
            wValue=timeout,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 1)  # Assuming success returns 1

    @patch("usb.core.find")
    def test_upload(self, mock_find):
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
        result = dfu._upload(mock_device, interface, transaction, data)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0xa1,
            bRequest=dfu.Request.UPLOAD,  # Assuming Request.UPLOAD
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=data,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, data)  # Assuming success returns bytes(10)

    @patch("usb.core.find")
    def test_dwnload(self, mock_find):
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
        result = dfu._download(mock_device, interface, transaction, data)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Request.DNLOAD,  # Assuming Request.DNLOAD
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=data,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, len(data))  # Assuming success returns 10

    @patch("usb.core.find")
    def test_get_status(self, mock_find):
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
        status = dfu._get_status(mock_device, interface)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0xa1,
            bRequest=dfu.Request.GETSTATUS,  # Assuming Request.GETSTATUS
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=length,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(status.bState, 0)  # Assuming success returns 0

    @patch("usb.core.find")
    def test_clear_status(self, mock_find):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 0

        # Calling the function
        interface = 0
        transaction = 0
        result = dfu._clear_status(mock_device, interface)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Request.CLRSTATUS,  # Assuming Request.CLRSTATUS
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 0)  # Assuming success returns 0

    @patch("usb.core.find")
    def test_abort(self, mock_find):
        # Mocking the device
        mock_device = MagicMock()

        # Mocking the return value of usb.core.find
        mock_find.return_value = mock_device

        # Mocking the return value of ctrl_transfer method
        mock_device.ctrl_transfer.return_value = 0

        # Calling the function
        interface = 0
        transaction = 0
        result = dfu._abort(mock_device, interface)

        # Assertions
        mock_device.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=dfu.Request.ABORT,  # Assuming Request.ABORT
            wValue=transaction,
            wIndex=interface,
            data_or_wLength=None,
            timeout=1000,  # Assuming TIMEOUT is 1000
        )
        self.assertEqual(result, 0)  # Assuming success returns 0


if __name__ == "__main__":
    unittest.main()
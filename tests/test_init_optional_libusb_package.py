"""
Regression test for the __init__.py crash bug: importing `pydfuutil`
must NEVER fail just because the optional `libusb_package` dependency
isn't installed (it moved from a hard dependency to the `libusb` extra).

Reproduces the original bug by simulating `import libusb_package` raising
ImportError, and asserts the package still imports and falls back to
DEFAULT_BACKEND = None (pyusb's own system-libusb discovery).
"""
import builtins
import importlib
import sys
import unittest


class TestPackageImportWithoutLibusbPackage(unittest.TestCase):
    def _reimport_with_libusb_package_missing(self):
        """Simulates a clean environment where `libusb_package` was never
        installed (e.g. after moving it to an optional extra)."""
        # drop any cached import of the package and its dependency so the
        # try/except path in __init__.py actually runs again
        for mod_name in list(sys.modules):
            if mod_name == "pydfuutil" or mod_name.startswith("pydfuutil."):
                del sys.modules[mod_name]
            if mod_name == "libusb_package":
                del sys.modules[mod_name]

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "libusb_package":
                raise ImportError("simulated: libusb_package not installed")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import  # ty: ignore[invalid-assignment]
        try:
            return importlib.import_module("pydfuutil")
        finally:
            builtins.__import__ = real_import

    def test_import_does_not_raise_without_libusb_package(self):
        try:
            pydfuutil = self._reimport_with_libusb_package_missing()
        except ImportError as e:
            self.fail(
                "importing pydfuutil must not fail when libusb_package is "
                f"absent (it's an optional extra now); raised: {e!r}"
            )

        self.assertIsNone(
            pydfuutil.DEFAULT_BACKEND,
            "DEFAULT_BACKEND should fall back to None (let pyusb search "
            "for a system libusb) when libusb_package is unavailable",
        )

    def test_default_backend_is_defined_attribute(self):
        """DEFAULT_BACKEND must always exist as a module attribute so
        downstream modules (dfu_util.py, __main__.py, lsusb.py) can import
        it unconditionally, regardless of which branch of the try/except
        ran at package-import time."""
        import pydfuutil

        self.assertTrue(hasattr(pydfuutil, "DEFAULT_BACKEND"))

    def tearDown(self):
        # leave a normal, real import of pydfuutil in sys.modules for any
        # tests that run after this one in the same session
        for mod_name in list(sys.modules):
            if mod_name == "pydfuutil" or mod_name.startswith("pydfuutil."):
                del sys.modules[mod_name]
        importlib.import_module("pydfuutil")


if __name__ == "__main__":
    unittest.main()

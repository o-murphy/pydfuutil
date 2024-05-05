import unittest
from time import sleep

from pydfuutil.progress import *

unittest.TestLoader.sortTestMethodsUsing = None


class TestDfuProgress(unittest.TestCase):

    def _loop(self, backend=None, total=None):
        i = 10

        with Progress(backend) as prog:
            name = (backend.__name__
                    if backend
                    else f"Any")

            prog.start_task(description=f"{name}",
                            total=total)
            while i >= 1:
                sleep(0.1)
                prog.update(advance=1)
                i -= 1
            prog.update(description=f"{name} OK")

    @unittest.skipIf(not TQDM_PROGRESS,
                     "package not installed ImportError/UnboundLocalError/AttributeError")
    def test_tqdm(self):
        self._loop(TqdmBackend, 10)

        with self.subTest("indeterminate"):
            self._loop(TqdmBackend, None)

    @unittest.skipIf(not RICH_PROGRESS,
                     "package not installed ImportError/UnboundLocalError/AttributeError")
    def test_rich(self):
        self._loop(RichBackend, 10)

        with self.subTest("indeterminate"):
            self._loop(RichBackend, None)

    def test_no_progress(self):
        self._loop(NoProgressBarBackend)

    def test_ascii(self):
        with self.subTest("by completed"):
            i, j = 20, 1
            n = AsciiBackend.__name__
            with Progress(AsciiBackend) as prog:
                prog.start_task(description=n,
                                total=i)
                while i >= 0:
                    sleep(0.1)
                    prog.update(completed=21-i)
                    i -= 1 + j
                    j += 1
                prog.update(description=f"{n} OK")

        with self.subTest("by advance"):
            self._loop(AsciiBackend, 10)

        with self.subTest("indeterminate"):
            self._loop(AsciiBackend, None)

    @unittest.skip("rich.errors.LiveError: Only one live display may be active at once")
    def test_autodetect(self):
        self._loop(None)

    def test_exception(self):
        i = 10
        with self.assertRaises(Exception):
            with Progress(AbstractProgressBackend) as prog:
                prog.start_task(description=f"OnError",
                                total=i)
                while i >= 1:
                    sleep(0.1)
                    prog.update(advance=1)
                    i -= 1
                    if i == 5:
                        raise Exception("Something went wrong")


if __name__ == "__main__":
    unittest.main()

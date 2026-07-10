"""
Progress bar utilities
(C) 2023 Yaroshenko Dmytro (https://github.com/o-murphy)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
from abc import ABC, abstractmethod
from typing import Any, Optional


RICH_PROGRESS: Any = None
try:
    from rich import progress as RICH_PROGRESS
except ImportError:
    try:
        from pip._vendor.rich import progress as RICH_PROGRESS  # ty: ignore[unresolved-import]
    except ImportError:
        pass

TQDM_PROGRESS: Any = None
try:
    from tqdm import tqdm as TQDM_PROGRESS
except ImportError:
    pass


import logging


_logger = logging.getLogger("progress")
_logger.setLevel(logging.INFO)


class AbstractProgressBackend(ABC):
    """Abstract class for progress bar backends"""

    def __init__(self): ...

    @abstractmethod
    def start(self):
        """
        Progress backend initialisation
        """

    @abstractmethod
    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        """
        Start progress task
        :param description:
        :param total:
        """

    @abstractmethod
    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        """
        Update progress task
        :param description:
        :param advance:
        :param completed:
        """

    @abstractmethod
    def fail(self):
        """Runs on Progress.__exit__ if ctx raises exception"""

    @abstractmethod
    def stop(self):
        """Stop progressbar backend"""


class NoProgressBarBackend(AbstractProgressBackend):
    """progress bar backend that does nothing"""

    def start(self):
        pass

    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        pass

    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        pass

    def fail(self):
        pass

    def stop(self):
        pass


class AsciiBackend(AbstractProgressBackend):
    """ASCII based progress bar backend"""

    BAR_WIDTH = 30
    REDIRECT_STD = True

    def __init__(self):
        super().__init__()
        self._value: Optional[int] = None
        self._total: Optional[int] = None
        self._rate: Optional[float] = None
        self._fail: Optional[bool] = None

    def _print(self, symbol: str):
        if self.REDIRECT_STD:
            sys.stdout.write(symbol)
            sys.stdout.flush()
        else:
            print(symbol, end="", flush=True)

    def start(self):
        pass

    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        self._value = 0
        self._total = total
        self._fail = False
        if total:
            self._rate = total / self.BAR_WIDTH
        self._print(f"{description} [")

    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        total = self._total
        if total:
            value = self._value
            rate = self._rate
            assert value is not None
            assert rate is not None
            if advance:
                value += advance
                if rate != 0 and advance % rate != 0:
                    self._print("━" * int(advance / rate))
            if completed:
                if completed < value:
                    raise ValueError(
                        f"The progress can't run backward! {completed} < {value}"
                    )
                prev_value = value
                value = completed
                if (delta := value - prev_value) > 0:
                    if delta % rate != 0:
                        self._print("━" * int(delta / rate))
            self._value = value
            if total <= value and (advance or completed):
                self._print("] Complete!\n")
        else:
            self._print("━")

    def fail(self):
        self._print("] Failed!\n")

    def stop(self):
        if not self._total and not self._fail:
            self._print("] Complete!\n")


class TqdmBackend(AbstractProgressBackend):
    """tqdm based progress bar backend"""

    BAR_FORMAT = (
        "{desc} {bar:20} {percentage:3.0f}% "
        "{remaining} {n_fmt}/{total_fmt} bytes {rate_fmt}"
    )
    BAR_FORMAT_INF = "{desc} {postfix} {n_fmt}/{total_fmt} bytes {rate_fmt}"

    def __init__(self):
        super().__init__()
        self._progress: Any = None
        self._value: Optional[int] = None
        self._spinner_state: Optional[int] = None

    def start(self):
        pass

    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        self._value = 0
        if total:
            self._progress = TQDM_PROGRESS(
                total=total,
                unit=" bytes",
                desc=description,
                bar_format=TqdmBackend.BAR_FORMAT,
                ascii=" ━",
            )
        else:
            self._progress = TQDM_PROGRESS(
                total=float("inf"),
                unit=" bytes",
                desc=description,
                bar_format=TqdmBackend.BAR_FORMAT_INF,
                postfix="",
            )
            self._spinner_state = 0

    def _spin(self, complete=False):
        progress = self._progress
        assert progress is not None
        if complete:
            progress.postfix = "━" * 20
            return

        spinner_state = self._spinner_state
        assert spinner_state is not None
        symbol = "=▶" if spinner_state % 2 == 1 else "▶="
        progress.postfix = symbol * 10
        self._spinner_state = spinner_state + 1

    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        progress = self._progress
        assert progress is not None
        if description:
            progress.desc = description

        if advance:
            progress.update(advance)
        if completed:
            progress.n = completed

        if progress.total:
            if progress.total == self._value and (advance or completed):
                progress.desc = description
        else:
            self._spin()
        progress.refresh()

    def fail(self):
        # self._progress.colour = "red"
        # self._progress.refresh()
        pass

    def stop(self):
        progress = self._progress
        assert progress is not None
        if not progress.total:
            self._spin(complete=True)
        self._progress = None


class RichBackend(AbstractProgressBackend):
    """Rich.progress based progress bar backend"""

    def __init__(self):
        super().__init__()
        self._progress: Any = None
        self._task_id: Any = None
        self._fail: Optional[bool] = None

    def start(self):
        pass

    def _prepare(self):
        self._progress = RICH_PROGRESS.Progress(
            RICH_PROGRESS.TextColumn("[progress.description]{task.description}"),
            RICH_PROGRESS.BarColumn(20),
            RICH_PROGRESS.TaskProgressColumn(),
            RICH_PROGRESS.TimeRemainingColumn(),
            RICH_PROGRESS.DownloadColumn(),
            RICH_PROGRESS.TransferSpeedColumn(),
        )
        self._progress.start()

    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        self._prepare()
        self._fail = False
        kwargs = {}
        if description is not None:
            kwargs["description"] = f"[#F92672]{description}"
        kwargs["total"] = total
        self._task_id = self._progress.add_task(start=True, **kwargs)

    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        kwargs = {}
        if description is not None:
            # kwargs["description"] = f"[rgb(249,38,114)]{description}"
            kwargs["description"] = f"[#F92672]{description}"
        if advance is not None:
            kwargs["advance"] = advance
        if completed is not None:
            kwargs["completed"] = completed
        self._progress.update(self._task_id, **kwargs)
        t = self._progress.tasks[self._task_id]
        if t.total is not None and t.completed >= t.total:
            desc = t.description.split("]")[-1]
            self._progress.update(self._task_id, description=f"[#729C1F]{desc}")

    def fail(self):
        self._fail = True
        t = self._progress.tasks[self._task_id]
        desc = t.description.split("]")[-1]
        self._progress.update(self._task_id, description=f"[red]{desc}")

    def stop(self):
        if not self._fail:
            t = self._progress.tasks[self._task_id]
            desc = t.description.split("]")[-1]
            self._progress.update(
                self._task_id, description=f"[#729C1F]{desc}", total=t.completed
            )
        # # uncomment to hide bar after complete
        # self._progress.remove_task(self._task_id)
        self._progress.stop()
        self._progress = None


def find_backend():
    """searching for an available backend"""
    if RICH_PROGRESS is not None:
        return RichBackend
    if TQDM_PROGRESS is not None:
        return TqdmBackend
    return AsciiBackend


class Progress:
    """
    High leveled progress bar class
    Use this as a context
    """

    __DEFAULT_BACKEND = find_backend()

    def __init__(self, backend=None):
        if backend is None:
            backend = Progress.__DEFAULT_BACKEND
        self._backend = backend()

    @classmethod
    def set_default_backend(cls, backend: type[AbstractProgressBackend]):
        """
        Sets the default progressbar backend
        :param backend:
        :return:
        """
        if not issubclass(backend, AbstractProgressBackend):
            raise TypeError("Invalid backend")
        cls.__DEFAULT_BACKEND = backend

    def start(self):
        """
        Progress backend initialisation
        """
        self._backend.start()

    def start_task(
        self, *, description: Optional[str] = None, total: Optional[int] = None
    ):
        """
        Start progress task
        :param description:
        :param total:
        """
        self._backend.start_task(description=description, total=total)

    def update(
        self,
        *,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        """
        Update progress task
        :param description:
        :param advance:
        :param completed:
        """
        self._backend.update(
            description=description, advance=advance, completed=completed
        )

    def stop(self):
        """Stop progressbar backend"""
        self._backend.stop()

    def fail(self):
        """
        Runs on progress __exit__ if ctx raises exception
        """
        self._backend.fail()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.fail()
            raise exc_type(exc_value)
        self.stop()
        return True


__all__ = (
    "Progress",
    "AsciiBackend",
    "RichBackend",
    "TqdmBackend",
    "RICH_PROGRESS",
    "TQDM_PROGRESS",
    "AbstractProgressBackend",
    "NoProgressBarBackend",
    "find_backend",
)

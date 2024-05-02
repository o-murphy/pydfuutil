"""Progress bar utilities"""


import sys
from abc import ABC, abstractmethod

try:
    from rich import progress as RICH_PROGRESS
except ImportError:
    try:
        from pip._vendor.rich import progress as RICH_PROGRESS
    except ImportError:
        RICH_PROGRESS = None

try:
    from tqdm import tqdm as TQDM_PROGRESS
except ImportError:
    TQDM_PROGRESS = None

import logging

_logger = logging.getLogger('progress')
_logger.setLevel(logging.INFO)


class AbstractProgressBackend(ABC):
    """Abstract class for progress bar backends"""

    def __init__(self):
        ...

    @abstractmethod
    def start(self):
        """
        Progress backend initialisation
        """

    @abstractmethod
    def start_task(self, *, description: str = None, total: int = None):
        """
        Start progress task
        :param description:
        :param total:
        """

    @abstractmethod
    def update(self, *, description: str = None, advance: int = None, completed: int = None):
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

    def start_task(self, *, description: str = None, total: int = None):
        pass

    def update(self, *, description: str = None, advance: int = None, completed: int = None):
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
        self._value = None
        self._total = None
        self._rate = None

    def _print(self, symbol: str):
        if self.REDIRECT_STD:
            sys.stdout.write(symbol)
            sys.stdout.flush()
        else:
            print(symbol, end="", flush=True)

    def start(self):
        pass

    def start_task(self, *, description: str = None, total: int = None):
        self._value = 0
        self._total = total
        self._rate = self._total / self.BAR_WIDTH
        self._print(f"{description} [")

    def update(self, *, description: str = None, advance: int = None, completed: int = None):
        if advance:
            self._value += advance
            if self._rate != 0 and self._value % self._rate != 0:
                # self._print("#")
                self._print("━")
        if completed:
            if completed < self._value:
                raise ValueError(f"The progress can't run backward! "
                                 f"{completed} < {self._value}")
            self._value = completed
            self._print("#" * (completed - self._value) // self._rate)
        if self._total == self._value and (advance or completed):
            self._print("] Complete!\n")

    def fail(self):
        self._print("] Failed!\n")

    def stop(self):
        pass


class TqdmBackend(AbstractProgressBackend):
    """tqdm based progress bar backend"""

    BAR_FORMAT = ("{desc} {bar:20} {percentage:3.0f}% "
                  "{remaining} {n_fmt}/{total_fmt} bytes {rate_fmt}")

    def __init__(self):
        super().__init__()
        self._progress = None
        self._value = None

    def start(self):
        pass

    def start_task(self, *, description: str = None, total: int = None):
        self._value = 0
        self._progress = TQDM_PROGRESS(
            total=total,
            unit=' bytes',
            desc=description,
            bar_format=TqdmBackend.BAR_FORMAT,
            colour="magenta",
            ascii=' ━',
        )

    def update(self, *, description: str = None, advance: int = None, completed: int = None):
        if description:
            self._progress.description = description
        if advance:
            self._progress.update(advance)
        if completed:
            self._progress.n = completed
        # if self._progress.total == self._value and (advance or completed):
        #     self._progress.colour = "green"
        #     self._progress.description = description
        self._progress.refresh()

    def fail(self):
        # self._progress.colour = "red"
        # self._progress.refresh()
        pass

    def stop(self):
        self._progress = None


class RichBackend(AbstractProgressBackend):
    """Rich.progress based progress bar backend"""

    def __init__(self):
        super().__init__()
        self._progress: [RICH_PROGRESS.Progress, None] = None
        self._task_id = None

    def start(self):
        pass

    def _prepare(self):
        self._progress = RICH_PROGRESS.Progress(
            RICH_PROGRESS.TextColumn(
                "[progress.description]{task.description}"),
            RICH_PROGRESS.BarColumn(20),
            RICH_PROGRESS.TaskProgressColumn(),
            RICH_PROGRESS.TimeRemainingColumn(),
            RICH_PROGRESS.DownloadColumn(),
            RICH_PROGRESS.TransferSpeedColumn(),
        )
        self._progress.start()

    def start_task(self, *, description: str = None, total: int = None):
        self._prepare()
        kwargs = {}
        if description is not None:
            kwargs["description"] = f"[#F92672]{description}"
        if total is not None:
            kwargs["total"] = total
        self._task_id = self._progress.add_task(start=True, **kwargs)

    def update(self, *, description: str = None, advance: int = None, completed: int = None):
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
        if t.completed == t.total:
            desc = t.description.split(']')[-1]
            self._progress.update(self._task_id,
                                  description=f"[#729C1F]{desc}")

    def fail(self):
        t = self._progress.tasks[self._task_id]
        desc = t.description.split(']')[-1]
        self._progress.update(self._task_id,
                              description=f"[red]{desc}")

    def stop(self):
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

    def start_task(self, *, description: str = None, total: int = None):
        """
        Start progress task
        :param description:
        :param total:
        """
        self._backend.start_task(description=description, total=total)

    def update(self, *, description: str = None, advance: int = None, completed: int = None):
        """
        Update progress task
        :param description:
        :param advance:
        :param completed:
        """
        self._backend.update(description=description, advance=advance, completed=completed)

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
            # print(exc_type, exc_value, traceback.tb_lineno)
            # raise Exception(exc_type, exc_value, traceback)
        self.stop()
        return True


__all__ = (
    'Progress',
    'AsciiBackend',
    'RichBackend',
    'TqdmBackend',
    'RICH_PROGRESS',
    'TQDM_PROGRESS',
    'AbstractProgressBackend',
    'NoProgressBarBackend',
    'find_backend'
)

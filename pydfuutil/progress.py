import sys

TqdmProgress = None
RichProgress = None
try:
    from rich import progress as RichProgress
except ImportError:
    try:
        from pip._vendor.rich import progress as RichProgress
    except ImportError:
        pass

try:
    from tqdm import tqdm as TqdmProgress
except ImportError:
    pass


import logging
_logger = logging.getLogger('progress')
_logger.setLevel(logging.INFO)


class AbstractProgressBackend:
    def __init__(self):
        pass

    def start(self):
        pass

    def start_task(self, description=None, total=None):
        pass

    def update(self, description=None, advance=None, completed=None):
        pass

    def fail(self):
        pass

    def stop(self):
        pass


class NoProgressBarBackend(AbstractProgressBackend):
    pass

class AsciiBackendAbstract(AbstractProgressBackend):
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

    def start_task(self, description=None, total=None):
        self._value = 0
        self._total = total
        self._rate = self._total / self.BAR_WIDTH
        self._print(f"{description} [")

    def update(self, description=None, advance=None, completed=None):
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
            self._print(f"] Complete!\n")

    def fail(self):
        self._print("] Failed!\n")

    def stop(self):
        pass




class TqdmBackendAbstract(AbstractProgressBackend):
    BAR_FORMAT = ("{desc} {bar:20} {percentage:3.0f}% "
                  "{remaining} {n_fmt}/{total_fmt} bytes {rate_fmt}")

    def __init__(self):
        super().__init__()
        self._progress = None
        self._value = None

    def start(self):
        pass

    def start_task(self, description=None, total=None):
        self._value = 0
        self._progress = TqdmProgress(
            total=total,
            unit=' bytes',
            desc=description,
            bar_format=TqdmBackendAbstract.BAR_FORMAT,
            colour="magenta",
            ascii=' ━',
        )

    def update(self, description=None, advance=None, completed=None):
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


class RichBackendAbstract(AbstractProgressBackend):

    def __init__(self):
        super().__init__()
        self._progress: [RichProgress.Progress, None] = None
        self._task_id = None

    def start(self):
        pass

    def _prepare(self):
        self._progress = RichProgress.Progress(
            RichProgress.TextColumn(
                "[progress.description]{task.description}"),
            RichProgress.BarColumn(20),
            RichProgress.TaskProgressColumn(),
            RichProgress.TimeRemainingColumn(),
            RichProgress.DownloadColumn(),
            RichProgress.TransferSpeedColumn(),
        )
        self._progress.start()

    def start_task(self, *, description=None, total=None):
        self._prepare()
        kwargs = {}
        if description is not None:
            kwargs["description"] = f"[#F92672]{description}"
        if total is not None:
            kwargs["total"] = total
        self._task_id = self._progress.add_task(start=True, **kwargs)

    def update(self, *, description=None, advance=None, completed=None):
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
    if RichProgress is not None:
        return RichBackendAbstract
    if TqdmProgress is not None:
        return TqdmBackendAbstract
    return AsciiBackendAbstract


class Progress:
    __DEFAULT_BACKEND = find_backend()

    def __init__(self, backend=None):
        if backend is None:
            backend = Progress.__DEFAULT_BACKEND
        self._backend = backend()

    @classmethod
    def set_default_backend(cls, backend: type[AbstractProgressBackend]):
        if not issubclass(backend, AbstractProgressBackend):
            raise TypeError("Invalid backend")
        cls.__DEFAULT_BACKEND = backend

    def start(self):
        self._backend.start()

    def start_task(self, *, description=None, total=None):
        self._backend.start_task(description=description, total=total)

    def update(self, *, description=None, advance=None, completed=None):
        self._backend.update(description=description, advance=advance, completed=completed)

    def stop(self):
        self._backend.stop()

    def fail(self):
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
    'AsciiBackendAbstract',
    'RichBackendAbstract',
    'TqdmBackendAbstract',
    'RichProgress',
    'TqdmProgress',
    'AbstractProgressBackend',
    'NoProgressBarBackend'
)

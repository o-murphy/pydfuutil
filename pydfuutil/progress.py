import sys

TqdmProgress = None
RichProgress = None
try:
    from rich import progress as RichProgress
except ImportError:
    try:
        from pip._vendor.rich import progress as RichProgress
    except ImportError:
        try:
            from tqdm import tqdm as TqdmProgress
        except ImportError:
            pass


def find_backend():
    if RichProgress is not None:
        return RichBackend
    if TqdmProgress is not None:
        return TqdmBackend
    return AsciiBackend


class ProgressBackend:
    def __init__(self):
        pass

    def start(self):
        pass

    def start_task(self, description=None, total=None):
        pass

    def update(self, description=None, advance=None, completed=None):
        pass

    def stop(self):
        pass


class AsciiBackend(ProgressBackend):
    BAR_WIDTH = 50
    REDIRECT_STD = True

    def __init__(self):
        super().__init__()
        self._value = None
        self._total = None
        self._rate = None

    def _print(self, symbol: str):
        sys.stdout.write(symbol) if self.REDIRECT_STD else print(symbol, end="")

    def start(self):
        self._value = 0

    def start_task(self, description=None, total=None):
        self._total = total
        self._rate = self._total // self.BAR_WIDTH
        self._print("[")

    def update(self, description=None, advance=None, completed=None):
        if advance:
            self._value += advance
            if self._value % self._rate != 0:
                self._print("#")
        if completed:
            if completed < self._value:
                raise ValueError(f"The progress can't run backward! "
                                 f"{completed} < {self._value}")
            self._value = completed
            self._print("#" * (completed - self._value) // self._rate)
        if self._total == self._value and (advance or completed):
            self._print("]\n")


class TqdmBackend(ProgressBackend):
    def __init__(self):
        super().__init__()
        self._progress = None
        self._value = None

    def start(self):
        pass

    def start_task(self, description=None, total=None):
        self._value = 0
        self._progress = TqdmProgress(total=total, desc=description)

    def update(self, description=None, advance=None, completed=None):
        if description:
            self._progress.description = description
        if advance:
            self._progress.update(advance)
        if completed:
            self._progress.n = completed
        self._progress.refresh()

    def stop(self):
        self._progress = None


class RichBackend(ProgressBackend):

    def __init__(self):
        super().__init__()
        self._progress: [RichProgress.Progress, None] = None
        self._task_id = None

    def start(self):
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

    def stop(self):
        self._progress.remove_task(self._task_id)
        self._progress.stop()
        self._progress = None


class DfuProgress:
    def __init__(self, backend=None):
        if backend is None:
            backend = find_backend()
        self._backend = backend()

    def start(self, **kwargs):
        self._backend.start(**kwargs)

    def start_task(self, *, description=None, total=None):
        self._backend.start_task(description=description, total=total)

    def update(self, *, description=None, advance=None, completed=None):
        self._backend.update(description=description, advance=advance, completed=completed)

    def stop(self):
        self._backend.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            print(exc_type, exc_value, traceback.tb_lineno)
            # raise Exception(exc_type, exc_value, traceback)
        self.stop()
        return True


from time import sleep

# i = 100
#
#
# with DfuProgress(TqdmBackend) as prog:
#     prog.start_task(description="count", total=i)
#     while i >= 1:
#         sleep(0.1)
#         prog.update(advance=1)
#         i -= 1
#
# i = 100
#
# with DfuProgress(RichBackend) as prog:
#     prog.start_task(description="count", total=i)
#     while i >= 1:
#         sleep(0.1)
#         prog.update(advance=1)
#         i -= 1

# i = 100
#
# with DfuProgress(AsciiBackend) as prog:
#     prog.start_task(description="count", total=i)
#     while i >= 1:
#         sleep(0.1)
#         prog.update(advance=1)
#         i -= 1

# i = 100
#
# with DfuProgress() as prog:
#     prog.start_task(description="count", total=i)
#     while i >= 1:
#         sleep(0.1)
#         prog.update(advance=1)
#         i -= 1

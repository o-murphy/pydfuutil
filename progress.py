from rich.progress import Progress, Task


class DfuProgress(Progress):

    """
    Task(id=0, description='[green]Flashing dfu
    modules...', total=0, completed=0, _get_time=<built-in
    function monotonic>, finished_time=0.0, visible=True,
    fields={}, finished_speed=None)
    """

    def __init__(self, *args, callback=None, **kwargs):
        super(DfuProgress, self).__init__(*args, **kwargs)
        self.callback = callback

    def update(self, task_id, *args, **kwargs) -> None:
        super(DfuProgress, self).update(task_id, *args, **kwargs)

        if callable(self.callback):
            task: Task = self._tasks[task_id]
            self.callback(task)
import asyncio


class JobTaskRegistry:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    def register(self, job_id: str, task: asyncio.Task) -> None:
        self._tasks[job_id] = task

    def get(self, job_id: str) -> asyncio.Task | None:
        return self._tasks.get(job_id)

    def cancel(self, job_id: str) -> bool:
        task = self._tasks.pop(job_id, None)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def remove(self, job_id: str) -> None:
        self._tasks.pop(job_id, None)

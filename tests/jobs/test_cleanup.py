import asyncio

from app.jobs.registry import JobRegistry
from app.jobs.runner import JobRunner


class TrackingCleanup:
    def __init__(self):
        self.deleted: list[str] = []

    def delete(self, path: str) -> None:
        self.deleted.append(path)


def test_runner_deletes_temp_data_after_success():
    registry = JobRegistry()
    cleanup = TrackingCleanup()
    job = registry.create(owner_key="test-owner")

    class Analyzer:
        async def analyze(self, audio: bytes) -> dict:
            return {"label": "normal"}

    asyncio.run(JobRunner(registry, Analyzer(), cleanup).run(job.job_id, b"audio", "temp.wav"))

    assert cleanup.deleted == ["temp.wav"]


def test_runner_deletes_temp_data_after_failure():
    registry = JobRegistry()
    cleanup = TrackingCleanup()
    job = registry.create(owner_key="test-owner")

    class FailingAnalyzer:
        async def analyze(self, audio: bytes) -> dict:
            raise RuntimeError("analysis failed")

    asyncio.run(JobRunner(registry, FailingAnalyzer(), cleanup).run(job.job_id, b"audio", "temp.wav"))

    assert cleanup.deleted == ["temp.wav"]


def test_runner_deletes_temp_data_after_cancellation():
    registry = JobRegistry()
    cleanup = TrackingCleanup()
    job = registry.create(owner_key="test-owner")
    registry.cancel(job.job_id)

    class Analyzer:
        async def analyze(self, audio: bytes) -> dict:
            return {"label": "normal"}

    asyncio.run(JobRunner(registry, Analyzer(), cleanup).run(job.job_id, b"audio", "temp.wav"))

    assert cleanup.deleted == ["temp.wav"]

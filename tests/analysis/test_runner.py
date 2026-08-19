import asyncio

from app.jobs.registry import JobRegistry
from app.jobs.runner import JobRunner
from tests.support.test_analyzer import TestAnalyzer


def test_runner_completes_job_with_injected_test_analyzer():
    registry = JobRegistry()
    job = registry.create(owner_key="test-owner")

    asyncio.run(JobRunner(registry, TestAnalyzer()).run(job.job_id, b"audio"))

    completed = registry.get(job.job_id)
    assert completed.status == "completed"
    assert completed.stage == "completed"
    assert completed.result["label"] == "normal"


def test_runner_marks_job_failed_when_analyzer_raises():
    class FailingAnalyzer:
        async def analyze(self, audio: bytes) -> dict:
            raise RuntimeError("model failure")

    registry = JobRegistry()
    job = registry.create(owner_key="test-owner")

    asyncio.run(JobRunner(registry, FailingAnalyzer()).run(job.job_id, b"audio"))

    failed = registry.get(job.job_id)
    assert failed.status == "failed"
    assert failed.stage == "failed"
    assert failed.error["error_code"] == "ANALYSIS.FAILED"

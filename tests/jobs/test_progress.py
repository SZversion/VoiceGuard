import asyncio

from app.jobs.registry import JobRegistry
from app.jobs.runner import JobRunner


STAGES = ["transcribing", "normalizing", "classifying", "risk_search", "finalizing"]


def test_new_job_starts_at_zero_progress():
    job = JobRegistry().create(owner_key="test-owner")
    assert job.progress == 0


def test_progress_aware_analyzer_reports_stages_in_order():
    class ProgressAnalyzer:
        async def analyze_with_progress(self, audio, report_stage):
            for stage in STAGES:
                report_stage(stage)
            return {"label": "normal"}

    registry = JobRegistry()
    job = registry.create(owner_key="test-owner")
    observed = []
    original_update = registry.update

    def record_update(job_id, **kwargs):
        updated = original_update(job_id, **kwargs)
        observed.append((updated.stage, updated.progress))
        return updated

    registry.update = record_update
    asyncio.run(JobRunner(registry, ProgressAnalyzer()).run(job.job_id, b"audio"))

    assert [stage for stage, _ in observed] == ["preprocessing", *STAGES, "completed"]
    progresses = [progress for _, progress in observed]
    assert all(left <= right for left, right in zip(progresses, progresses[1:]))
    assert registry.get(job.job_id).progress == 100


def test_legacy_analyzer_still_completes_with_progress():
    class LegacyAnalyzer:
        async def analyze(self, audio: bytes) -> dict:
            return {"label": "normal"}

    registry = JobRegistry()
    job = registry.create(owner_key="test-owner")
    asyncio.run(JobRunner(registry, LegacyAnalyzer()).run(job.job_id, b"audio"))

    completed = registry.get(job.job_id)
    assert completed.status == "completed"
    assert completed.progress == 100


def test_streaming_analyzer_reports_chunk_progress_to_job_registry():
    class StreamingAnalyzer:
        async def analyze_with_progress(self, audio, report_stage, report_progress):
            report_stage("transcribing")
            report_progress({
                "stage": "classifying",
                "transcribed_chunks": 2,
                "normalized_chunks": 2,
                "classified_chunks": 1,
                "total_chunks": 3,
            })
            return {"label": "normal"}

    registry = JobRegistry()
    job = registry.create(owner_key="test-owner")

    asyncio.run(JobRunner(registry, StreamingAnalyzer()).run(job.job_id, b"audio"))

    completed = registry.get(job.job_id)
    assert completed.status == "completed"
    assert completed.progress > 65
    assert completed.metadata == {
        "stage": "classifying",
        "transcribed_chunks": 2,
        "normalized_chunks": 2,
        "classified_chunks": 1,
        "total_chunks": 3,
    }
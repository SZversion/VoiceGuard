import pytest

from app.jobs.registry import InvalidJobTransition, JobRegistry


def test_create_job_assigns_id_and_queued_state():
    registry = JobRegistry()
    job = registry.create(owner_key="ip_hash")

    assert job.job_id.startswith("job_")
    assert job.status == "queued"
    assert job.stage == "queued"
    assert registry.get(job.job_id) == job


def test_job_can_move_through_running_and_completed_states():
    registry = JobRegistry()
    job = registry.create(owner_key="ip_hash")

    registry.update(job.job_id, status="running", stage="preprocessing")
    registry.update(job.job_id, status="completed", stage="completed", result={"label": "normal"})

    completed = registry.get(job.job_id)
    assert completed.status == "completed"
    assert completed.stage == "completed"
    assert completed.result == {"label": "normal"}


def test_cancel_running_job_discards_result_and_marks_cancelled():
    registry = JobRegistry()
    job = registry.create(owner_key="ip_hash")
    registry.update(job.job_id, status="running", stage="transcribing")

    cancelled = registry.cancel(job.job_id)

    assert cancelled is True
    assert registry.get(job.job_id).status == "cancelled"
    assert registry.get(job.job_id).stage == "cancelled"
    assert registry.get(job.job_id).result is None


def test_completed_job_cannot_be_cancelled():
    registry = JobRegistry()
    job = registry.create(owner_key="ip_hash")
    registry.update(job.job_id, status="running", stage="preprocessing")
    registry.update(job.job_id, status="completed", stage="completed", result={"label": "normal"})

    assert registry.cancel(job.job_id) is False
    assert registry.get(job.job_id).status == "completed"


def test_invalid_transition_raises_error():
    registry = JobRegistry()
    job = registry.create(owner_key="ip_hash")

    with pytest.raises(InvalidJobTransition):
        registry.update(job.job_id, status="completed", stage="completed")


def test_unknown_job_returns_none():
    assert JobRegistry().get("job_missing") is None

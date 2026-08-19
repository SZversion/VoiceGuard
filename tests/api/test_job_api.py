from fastapi.testclient import TestClient

from app.api.main import app
from app.jobs.registry import JobRegistry


def setup_function():
    app.state.job_registry = JobRegistry()


def test_status_returns_job_state_without_sensitive_fields():
    job = app.state.job_registry.create(owner_key="hashed-ip")
    app.state.job_registry.update(job.job_id, status="running", stage="transcribing")

    response = TestClient(app).get(f"/api/analyze/{job.job_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.job_id,
        "status": "running",
        "stage": "transcribing",
    }


def test_result_returns_completed_result():
    job = app.state.job_registry.create(owner_key="hashed-ip")
    app.state.job_registry.update(
        job.job_id,
        status="running",
        stage="finalizing",
    )
    app.state.job_registry.update(
        job.job_id,
        status="completed",
        stage="completed",
        result={"label": "normal", "suspicion_score": 0.1},
    )

    response = TestClient(app).get(f"/api/analyze/{job.job_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.job_id,
        "result": {"label": "normal", "suspicion_score": 0.1},
    }


def test_result_rejects_incomplete_job():
    job = app.state.job_registry.create(owner_key="hashed-ip")

    response = TestClient(app).get(f"/api/analyze/{job.job_id}/result")

    assert response.status_code == 409
    assert response.json()["error_code"] == "JOB.NOT_COMPLETED"


def test_cancel_returns_cancelled_state():
    job = app.state.job_registry.create(owner_key="hashed-ip")
    app.state.job_registry.update(job.job_id, status="running", stage="transcribing")

    response = TestClient(app).delete(f"/api/analyze/{job.job_id}")

    assert response.status_code == 200
    assert response.json() == {"job_id": job.job_id, "status": "cancelled"}


def test_unknown_job_returns_common_not_found_error():
    response = TestClient(app).get("/api/analyze/job_missing/status")

    assert response.status_code == 404
    assert response.json()["error_code"] == "JOB.NOT_FOUND"


def test_completed_job_cannot_be_cancelled():
    job = app.state.job_registry.create(owner_key="hashed-ip")
    app.state.job_registry.update(job.job_id, status="running", stage="finalizing")
    app.state.job_registry.update(
        job.job_id,
        status="completed",
        stage="completed",
        result={"label": "normal"},
    )

    response = TestClient(app).delete(f"/api/analyze/{job.job_id}")

    assert response.status_code == 409
    assert response.json()["error_code"] == "JOB.CANNOT_CANCEL"

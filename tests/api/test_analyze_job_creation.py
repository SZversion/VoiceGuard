from io import BytesIO

from fastapi.testclient import TestClient

from app.api.main import app
from app.jobs.registry import JobRegistry
from tests.support.test_analyzer import TestAnalyzer


def test_analyze_creates_job_when_analyzer_is_injected():
    app.state.job_registry = JobRegistry()
    app.state.analyzer = TestAnalyzer()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/analyze",
                files={
                    "audio": (
                        "call.wav",
                        BytesIO(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 8),
                        "audio/wav",
                    )
                },
            )
    finally:
        app.state.analyzer = None

    assert response.status_code == 202
    assert response.json()["job_id"].startswith("job_")
    assert response.json()["status"] == "queued"

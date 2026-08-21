from io import BytesIO

from fastapi.testclient import TestClient

from app.api.main import app
from app.core.request_controls import DuplicateJobLock, IpHasher, RateLimiter
from app.jobs.cleanup import TempDataStore
from app.jobs.registry import JobRegistry
from tests.support.test_analyzer import TestAnalyzer


WAV = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 8


def _configure_controls(*, max_requests: int, lock: DuplicateJobLock | None = None):
    app.state.job_registry = JobRegistry()
    app.state.analyzer = TestAnalyzer()
    app.state.temp_data_store = TempDataStore()
    app.state.ip_hasher = IpHasher("test-secret")
    app.state.job_lock = lock or DuplicateJobLock()
    app.state.rate_limiter = RateLimiter(max_requests=max_requests, window_seconds=60)


def _audio_file():
    return {"audio": ("call.wav", BytesIO(WAV), "audio/wav")}


def test_analyze_rejects_rate_limited_owner():
    _configure_controls(max_requests=1)

    try:
        client = TestClient(app)
        first = client.post("/api/analyze", files=_audio_file())
        second = client.post("/api/analyze", files=_audio_file())
    finally:
        app.state.analyzer = None

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["error_code"] == "SERVICE.RATE_LIMITED"


def test_analyze_rejects_duplicate_active_job():
    lock = DuplicateJobLock()
    owner_key = IpHasher("test-secret").hash_ip("testclient")
    lock.acquire(owner_key, "existing-job")
    _configure_controls(max_requests=10, lock=lock)

    try:
        response = TestClient(app).post("/api/analyze", files=_audio_file())
    finally:
        app.state.analyzer = None

    assert response.status_code == 409
    assert response.json()["error_code"] == "JOB.DUPLICATE"

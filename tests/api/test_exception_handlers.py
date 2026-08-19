from fastapi.testclient import TestClient

from app.api.main import app


def test_missing_audio_returns_common_request_error():
    response = TestClient(app).post("/api/analyze", data={})

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "REQUEST.INVALID"
    assert body["stage"] == "request_validation"
    assert body["retryable"] is False
    assert body["request_id"].startswith("req_")


def test_unexpected_exception_uses_fixed_message():
    response = TestClient(app, raise_server_exceptions=False).get("/api/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "INTERNAL.ERROR"
    assert body["message"] == "서버 내부 오류가 발생했습니다."
    assert body["stage"] == "server"
    assert body["request_id"].startswith("req_")

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_health_returns_server_status_without_loading_models():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_status_reports_models_not_ready():
    response = client.get("/api/model-status")

    assert response.status_code == 200
    assert response.json() == {
        "stt": "not_ready",
        "classifier": "not_ready",
        "analyzable": False,
    }


def test_docs_endpoint_is_available():
    response = client.get("/docs")

    assert response.status_code == 200

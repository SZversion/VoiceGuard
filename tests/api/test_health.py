from fastapi.testclient import TestClient

from app.api.main import app, create_app


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

class FakeClassifier:
    pass


def test_model_status_reports_classifier_ready_after_startup():
    test_app = create_app(classifier_loader=lambda: FakeClassifier())

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.status_code == 200
    assert response.json() == {
        "stt": "not_ready",
        "classifier": "ready",
        "analyzable": False,
    }


def test_model_status_reports_classifier_error_when_startup_loading_fails():
    def failing_loader():
        raise RuntimeError("model unavailable")

    test_app = create_app(classifier_loader=failing_loader)

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.status_code == 200
    assert response.json() == {
        "stt": "not_ready",
        "classifier": "error",
        "analyzable": False,
    }

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


def failing_stt_loader():
    raise RuntimeError("stt unavailable")


def test_model_status_reports_classifier_ready_when_stt_is_unavailable():
    test_app = create_app(
        stt_loader=failing_stt_loader,
        classifier_loader=lambda: FakeClassifier(),
    )

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.status_code == 200
    assert response.json() == {
        "stt": "error",
        "classifier": "ready",
        "analyzable": False,
    }


def test_model_status_reports_loader_errors():
    def failing_classifier_loader():
        raise RuntimeError("classifier unavailable")

    test_app = create_app(
        stt_loader=failing_stt_loader,
        classifier_loader=failing_classifier_loader,
    )

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.status_code == 200
    assert response.json() == {
        "stt": "error",
        "classifier": "error",
        "analyzable": False,
    }
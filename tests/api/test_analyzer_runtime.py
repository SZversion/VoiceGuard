from io import BytesIO

from fastapi.testclient import TestClient

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.api.main import create_app


class FakeTranscriber:
    async def transcribe(self, audio: bytes) -> str:
        return "정상적인 상담 내용입니다."


class FakeClassifier:
    def classify(self, transcript: str):
        return type(
            "Result",
            (),
            {
                "label": "normal",
                "suspicion_score": 0.1,
            },
        )()


def wav_bytes() -> bytes:
    return b"RIFF" + bytes(4) + b"WAVE" + bytes(8)


def test_runtime_creates_analyzer_when_both_models_are_ready():
    test_app = create_app(
        stt_loader=FakeTranscriber,
        classifier_loader=FakeClassifier,
    )

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

        assert response.json() == {
            "stt": "ready",
            "classifier": "ready",
            "analyzable": True,
        }
        assert isinstance(test_app.state.analyzer, VoicePhishingAnalyzer)


def test_runtime_keeps_analyzer_unavailable_when_stt_loading_fails():
    def failing_stt_loader():
        raise RuntimeError("stt unavailable")

    test_app = create_app(
        stt_loader=failing_stt_loader,
        classifier_loader=FakeClassifier,
    )

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.json() == {
        "stt": "error",
        "classifier": "ready",
        "analyzable": False,
    }
    assert test_app.state.analyzer is None


def test_runtime_logs_loader_failure_without_exposing_hf_token(caplog):
    def failing_stt_loader():
        raise RuntimeError("download failed with token hf_secret_value")

    test_app = create_app(
        stt_loader=failing_stt_loader,
        classifier_loader=FakeClassifier,
    )

    with caplog.at_level("ERROR"):
        with TestClient(test_app):
            pass

    assert "stt" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "download failed" in caplog.text
    assert "hf_secret_value" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_runtime_keeps_analyzer_unavailable_when_classifier_loading_fails():
    def failing_classifier_loader():
        raise RuntimeError("classifier unavailable")

    test_app = create_app(
        stt_loader=FakeTranscriber,
        classifier_loader=failing_classifier_loader,
    )

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert response.json() == {
        "stt": "ready",
        "classifier": "error",
        "analyzable": False,
    }
    assert test_app.state.analyzer is None


def test_analyze_creates_job_when_runtime_is_ready():
    test_app = create_app(
        stt_loader=FakeTranscriber,
        classifier_loader=FakeClassifier,
    )

    with TestClient(test_app) as client:
        response = client.post(
            "/api/analyze",
            files={"audio": ("call.wav", BytesIO(wav_bytes()), "audio/wav")},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_analyze_remains_unavailable_when_runtime_is_not_ready():
    def failing_stt_loader():
        raise RuntimeError("stt unavailable")

    test_app = create_app(
        stt_loader=failing_stt_loader,
        classifier_loader=FakeClassifier,
    )

    with TestClient(test_app) as client:
        response = client.post(
            "/api/analyze",
            files={"audio": ("call.wav", BytesIO(wav_bytes()), "audio/wav")},
        )

    assert response.status_code == 503
    assert response.json()["error_code"] == "MODEL.NOT_READY"
def test_default_runtime_uses_onnx_classifier_loader(monkeypatch):
    calls = []

    def fake_onnx_loader():
        calls.append("onnx")
        return FakeClassifier()

    import app.api.main as main_module

    monkeypatch.delenv("CLASSIFIER_BACKEND", raising=False)
    monkeypatch.setattr(main_module, "load_onnx_classifier", fake_onnx_loader)
    test_app = main_module.create_app(stt_loader=FakeTranscriber)

    with TestClient(test_app) as client:
        response = client.get("/api/model-status")

    assert calls == ["onnx"]
    assert response.json()["analyzable"] is True

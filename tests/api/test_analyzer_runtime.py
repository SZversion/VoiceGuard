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
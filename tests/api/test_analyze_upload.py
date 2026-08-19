from io import BytesIO

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_analyze_rejects_unsupported_extension():
    response = client.post(
        "/api/analyze",
        files={"audio": ("call.txt", BytesIO(b"not audio"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "AUDIO.UNSUPPORTED_FORMAT"


def test_analyze_rejects_empty_audio_file():
    response = client.post(
        "/api/analyze",
        files={"audio": ("call.wav", BytesIO(b""), "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "AUDIO.EMPTY"


def test_analyze_rejects_invalid_audio_signature():
    response = client.post(
        "/api/analyze",
        files={"audio": ("call.wav", BytesIO(b"not a wav"), "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "AUDIO.INVALID_FORMAT"


def test_analyze_returns_model_not_ready_for_valid_wav():
    wav_header = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 8

    response = client.post(
        "/api/analyze",
        files={"audio": ("call.wav", BytesIO(wav_header), "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == "MODEL.NOT_READY"

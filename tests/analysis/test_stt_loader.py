import pytest

from app.analysis.stt_loader import STTModelLoadError, load_stt_transcriber


class FakeWhisperModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_loader_creates_transcriber_with_configured_factory():
    calls = []

    def factory(**kwargs):
        calls.append(kwargs)
        return FakeWhisperModel(**kwargs)

    transcriber = load_stt_transcriber(
        model_size="medium",
        device="cpu",
        compute_type="int8",
        model_factory=factory,
    )

    assert transcriber.model.kwargs == {
        "model_size_or_path": "medium",
        "device": "cpu",
        "compute_type": "int8",
    }
    assert calls == [transcriber.model.kwargs]


def test_loader_wraps_factory_failure():
    def failing_factory(**kwargs):
        raise RuntimeError("model unavailable")

    with pytest.raises(STTModelLoadError):
        load_stt_transcriber(model_factory=failing_factory)
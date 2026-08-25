import pytest

from app.analysis.whisper_lora_loader import (
    ADAPTER_MODEL,
    BASE_MODEL,
    STTModelLoadError,
    load_whisper_lora_transcriber,
)


class FakeProcessor:
    pass


class FakeBaseModel:
    def eval(self):
        return self


class FakeAdapterModel:
    def eval(self):
        return self


def test_loader_applies_adapter_to_requested_base_model(monkeypatch):
    processor_calls = []
    base_calls = []
    base_models = []
    adapter_calls = []

    def processor_factory(model_id):
        processor_calls.append(model_id)
        return FakeProcessor()

    def base_factory(model_id):
        base_calls.append(model_id)
        model = FakeBaseModel()
        base_models.append(model)
        return model

    def adapter_factory(base_model, adapter_model):
        adapter_calls.append((base_model, adapter_model))
        return FakeAdapterModel()

    monkeypatch.setenv("STT_MAX_NEW_TOKENS", "64")
    monkeypatch.setenv("STT_AUDIO_CHUNK_SECONDS", "30")

    transcriber = load_whisper_lora_transcriber(
        processor_factory=processor_factory,
        base_model_factory=base_factory,
        adapter_factory=adapter_factory,
    )

    assert processor_calls == [BASE_MODEL]
    assert base_calls == [BASE_MODEL]
    assert adapter_calls == [(base_models[0], ADAPTER_MODEL)]
    assert transcriber.processor.__class__ is FakeProcessor
    assert transcriber.model.__class__ is FakeAdapterModel
    assert transcriber.max_new_tokens == 64
    assert transcriber.chunk_seconds == 30.0


def test_loader_wraps_model_loading_failure():
    def failing_base_factory(model_id):
        raise RuntimeError("model unavailable")

    with pytest.raises(STTModelLoadError) as error_info:
        load_whisper_lora_transcriber(
            processor_factory=lambda model_id: FakeProcessor(),
            base_model_factory=failing_base_factory,
        )

    assert "model unavailable" in str(error_info.value)
    assert isinstance(error_info.value.__cause__, RuntimeError)
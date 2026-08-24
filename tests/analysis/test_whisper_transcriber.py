import asyncio

import pytest

from app.analysis.whisper_transcriber import (
    AudioInputError,
    WhisperLoRATranscriber,
    TranscriptionError,
)


class FakeProcessor:
    def __init__(self):
        self.processor_calls = []
        self.decode_calls = []

    def __call__(self, waveform, sampling_rate, return_tensors, return_attention_mask):
        self.processor_calls.append((waveform, sampling_rate, return_tensors, return_attention_mask))
        return {"input_features": ["features"]}

    def batch_decode(self, generated_ids, skip_special_tokens):
        self.decode_calls.append((generated_ids, skip_special_tokens))
        return [" 한국어 전사 결과 "]


class FakeModel:
    def __init__(self):
        self.generate_calls = []

    def generate(self, **inputs):
        self.generate_calls.append(inputs)
        return ["generated ids"]


def fake_decoder(audio: bytes):
    return [0.1, 0.2], 16000


def test_transcriber_runs_processor_generate_and_decode():
    processor = FakeProcessor()
    model = FakeModel()
    transcriber = WhisperLoRATranscriber(
        processor,
        model,
        decoder=fake_decoder,
    )

    transcript = asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert transcript == "한국어 전사 결과"
    assert processor.processor_calls == [([0.1, 0.2], 16000, "pt", True)]
    assert model.generate_calls == [{"input_features": ["features"]}]
    assert processor.decode_calls == [(["generated ids"], True)]


def test_transcriber_rejects_empty_audio():
    transcriber = WhisperLoRATranscriber(
        FakeProcessor(),
        FakeModel(),
        decoder=fake_decoder,
    )

    with pytest.raises(AudioInputError):
        asyncio.run(transcriber.transcribe(b""))


def test_transcriber_wraps_decode_or_inference_failure():
    def failing_decoder(audio: bytes):
        raise RuntimeError("decode failed")

    transcriber = WhisperLoRATranscriber(
        FakeProcessor(),
        FakeModel(),
        decoder=failing_decoder,
    )

    with pytest.raises(TranscriptionError) as error_info:
        asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert "decode failed" in str(error_info.value)
    assert isinstance(error_info.value.__cause__, RuntimeError)
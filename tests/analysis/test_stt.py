import asyncio
from pathlib import Path

import pytest

from app.analysis.stt import (
    AudioInputError,
    FasterWhisperTranscriber,
    TranscriptionError,
    UnsupportedLanguageError,
)


class FakeSegment:
    def __init__(self, text: str):
        self.text = text


class FakeInfo:
    def __init__(self, language: str | None):
        self.language = language


class FakeWhisperModel:
    def __init__(self, language: str = "ko", segments=None, error: Exception | None = None):
        self.language = language
        self.segments = segments if segments is not None else [FakeSegment(" 의심스러운 송금 요청입니다. ")]
        self.error = error
        self.calls: list[str] = []
        self.requested_languages: list[str | None] = []

    def transcribe(self, audio_path: str, language: str | None = None):
        self.calls.append(audio_path)
        self.requested_languages.append(language)
        if self.error:
            raise self.error
        return iter(self.segments), FakeInfo(self.language)


def test_transcriber_returns_korean_transcript_and_removes_temp_file(tmp_path: Path):
    model = FakeWhisperModel()
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    transcript = asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert transcript == "의심스러운 송금 요청입니다."
    assert len(model.calls) == 1
    assert not Path(model.calls[0]).exists()


def test_transcriber_rejects_empty_audio_without_calling_model(tmp_path: Path):
    model = FakeWhisperModel()
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    with pytest.raises(AudioInputError):
        asyncio.run(transcriber.transcribe(b""))

    assert model.calls == []


def test_transcriber_rejects_non_korean_audio(tmp_path: Path):
    model = FakeWhisperModel(language="en")
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    with pytest.raises(UnsupportedLanguageError):
        asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert not Path(model.calls[0]).exists()


def test_transcriber_rejects_empty_transcript(tmp_path: Path):
    model = FakeWhisperModel(segments=[FakeSegment(" "), FakeSegment("")])
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    with pytest.raises(TranscriptionError):
        asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert not Path(model.calls[0]).exists()


def test_transcriber_wraps_model_failure_and_removes_temp_file(tmp_path: Path):
    model = FakeWhisperModel(error=RuntimeError("inference failed"))
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    with pytest.raises(TranscriptionError):
        asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert not Path(model.calls[0]).exists()
def test_transcriber_leaves_language_detection_to_whisper(tmp_path: Path):
    model = FakeWhisperModel()
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert model.requested_languages == [None]


def test_transcriber_preserves_segment_spacing(tmp_path: Path):
    model = FakeWhisperModel(
        segments=[FakeSegment("첫 번째 문장 "), FakeSegment("두 번째 문장")]
    )
    transcriber = FasterWhisperTranscriber(model, temp_dir=tmp_path)

    transcript = asyncio.run(transcriber.transcribe(b"audio bytes"))

    assert transcript == "첫 번째 문장 두 번째 문장"
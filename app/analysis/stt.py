import asyncio
import tempfile
from pathlib import Path
from typing import Any


class STTError(RuntimeError):
    """Base error for speech-to-text failures."""


class AudioInputError(STTError):
    """Raised when audio input is invalid."""


class UnsupportedLanguageError(STTError):
    """Raised when the detected language is not supported."""


class TranscriptionError(STTError):
    """Raised when transcription cannot produce usable text."""


class FasterWhisperTranscriber:
    """Adapt a Faster-Whisper model to the application Transcriber contract."""

    def __init__(
        self,
        model: Any,
        language: str = "ko",
        temp_dir: str | Path | None = None,
    ):
        self.model = model
        self.language = language
        self.temp_dir = temp_dir

    async def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise AudioInputError("audio must not be empty")

        temp_path = self._write_temp_audio(audio)
        try:
            segments, info = await asyncio.to_thread(self._run_model, temp_path)
            if getattr(info, "language", None) != self.language:
                raise UnsupportedLanguageError("only Korean audio is supported")

            transcript = "".join(
                str(getattr(segment, "text", "")) for segment in segments
            ).strip()
            if not transcript:
                raise TranscriptionError("transcription returned no text")
            return transcript
        except (UnsupportedLanguageError, TranscriptionError):
            raise
        except Exception as exc:
            raise TranscriptionError("speech transcription failed") from exc
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _write_temp_audio(self, audio: bytes) -> str:
        with tempfile.NamedTemporaryFile(
            dir=self.temp_dir,
            suffix=".audio",
            delete=False,
        ) as temp_file:
            temp_file.write(audio)
            return temp_file.name

    def _run_model(self, temp_path: str):
        segments, info = self.model.transcribe(temp_path)
        return list(segments), info
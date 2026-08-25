import asyncio
import io
from collections.abc import Callable
from typing import Any

from app.analysis.audio_chunking import (
    AudioChunk,
    TranscriptChunk,
    encode_wav_chunk,
    split_audio_bytes,
)


class STTError(RuntimeError):
    """Base error for Whisper transcription failures."""


class AudioInputError(STTError):
    """Raised when audio input is empty or invalid."""


class TranscriptionError(STTError):
    """Raised when Whisper cannot produce a transcript."""


def _decode_audio(audio: bytes):
    try:
        import soundfile as sf
        import torch
        import torchaudio
    except ImportError as exc:
        raise TranscriptionError(
            "Whisper audio dependencies are not installed."
        ) from exc

    try:
        samples, sample_rate = sf.read(
            io.BytesIO(audio),
            dtype="float32",
            always_2d=True,
        )
        waveform = torch.from_numpy(samples).transpose(0, 1).contiguous()
        waveform = waveform.mean(dim=0)
        if sample_rate != 16_000:
            waveform = torchaudio.functional.resample(
                waveform,
                sample_rate,
                16_000,
            )
            sample_rate = 16_000
        return waveform.to(dtype=torch.float32), sample_rate
    except Exception as exc:
        raise TranscriptionError(
            f"audio decoding failed ({type(exc).__name__}: {exc})"
        ) from exc


class WhisperLoRATranscriber:
    """Use a PEFT-adapted Whisper model through the Transcriber contract."""

    def __init__(
        self,
        processor: Any,
        model: Any,
        decoder: Callable[[bytes], tuple[Any, int]] = _decode_audio,
        device: str = "cpu",
        max_new_tokens: int = 128,
        chunk_seconds: float = 30.0,
        audio_splitter=None,
    ):
        self.processor = processor
        self.model = model
        self.decoder = decoder
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.chunk_seconds = chunk_seconds
        self.audio_splitter = audio_splitter or (
            lambda audio: split_audio_bytes(audio, self.decoder, self.chunk_seconds)
        )

    async def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise AudioInputError("audio must not be empty")

        try:
            return await asyncio.to_thread(self._transcribe_sync, audio)
        except (AudioInputError, TranscriptionError):
            raise
        except Exception as exc:
            raise TranscriptionError("speech transcription failed") from exc

    async def transcribe_chunks(self, audio: bytes) -> list[TranscriptChunk]:
        if not audio:
            raise AudioInputError("audio must not be empty")

        try:
            chunks: list[AudioChunk] = await asyncio.to_thread(
                self.audio_splitter,
                audio,
            )
            transcripts = []
            for chunk in chunks:
                chunk_audio = chunk.audio
                if not isinstance(chunk_audio, bytes):
                    chunk_audio = encode_wav_chunk(chunk, 16_000)
                transcript = await self.transcribe(chunk_audio)
                transcripts.append(
                    TranscriptChunk(chunk.start, chunk.end, transcript)
                )
            return transcripts
        except (AudioInputError, TranscriptionError):
            raise
        except Exception as exc:
            raise TranscriptionError(
                f"audio chunk transcription failed ({type(exc).__name__}: {exc})"
            ) from exc

    def _transcribe_sync(self, audio: bytes) -> str:
        try:
            waveform, sample_rate = self.decoder(audio)
            inputs = self.processor(
                waveform,
                sampling_rate=sample_rate,
                return_tensors="pt",
                return_attention_mask=True,
            )
            if hasattr(inputs, "to"):
                inputs = inputs.to(self.device)

            import torch

            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                )
            texts = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError(
                f"Whisper inference failed ({type(exc).__name__}: {exc})"
            ) from exc

        transcript = str(texts[0] if texts else "").strip()
        if not transcript:
            raise TranscriptionError("transcription returned no text")
        return transcript
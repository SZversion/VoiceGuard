from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AudioChunk:
    audio: Any
    start: float
    end: float


@dataclass(frozen=True)
class TranscriptChunk:
    start: float
    end: float
    transcript: str


def split_waveform(
    waveform: Any,
    sample_rate: int,
    chunk_seconds: float = 30.0,
) -> list[AudioChunk]:
    if sample_rate <= 0 or chunk_seconds <= 0:
        raise ValueError("sample_rate and chunk_seconds must be positive")

    if hasattr(waveform, "detach"):
        waveform = waveform.detach().cpu().numpy()

    sample_count = len(waveform)
    chunk_size = max(1, int(sample_rate * chunk_seconds))
    chunks: list[AudioChunk] = []

    for start_index in range(0, sample_count, chunk_size):
        end_index = min(start_index + chunk_size, sample_count)
        chunks.append(
            AudioChunk(
                audio=waveform[start_index:end_index],
                start=start_index / sample_rate,
                end=end_index / sample_rate,
            )
        )
    return chunks


def split_audio_bytes(
    audio: bytes,
    decoder: Callable[[bytes], tuple[Any, int]],
    chunk_seconds: float = 30.0,
) -> list[AudioChunk]:
    waveform, sample_rate = decoder(audio)
    return split_waveform(waveform, sample_rate, chunk_seconds)


def encode_wav_chunk(chunk: AudioChunk, sample_rate: int) -> bytes:
    try:
        import io
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError("soundfile is required for audio chunk encoding") from exc

    waveform = chunk.audio
    if hasattr(waveform, "detach"):
        waveform = waveform.detach().cpu().numpy()

    output = io.BytesIO()
    sf.write(output, waveform, sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()

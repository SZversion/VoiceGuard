"""Load the explicitly converted, merged Whisper LoRA model for CPU inference."""

import json
import os
from pathlib import Path

from app.analysis.whisper_lora_loader import (
    ADAPTER_MODEL,
    BASE_MODEL,
    STTModelLoadError,
    load_whisper_lora_transcriber,
)
from app.analysis.whisper_transcriber import (
    TranscriptionError,
    WhisperLoRATranscriber,
    _decode_audio,
)


DEFAULT_MODEL_PATH = "models/whisper-lora/ct2-int8"


class CTranslateWhisperTranscriber(WhisperLoRATranscriber):
    """Preserve audio chunk boundaries while replacing only inference."""

    def __init__(self, model, decoder=_decode_audio, max_new_tokens=128, chunk_seconds=30.0):
        super().__init__(None, model, decoder=decoder, max_new_tokens=max_new_tokens,
                         chunk_seconds=chunk_seconds)

    def _transcribe_sync(self, audio: bytes) -> str:
        try:
            waveform, sample_rate = self.decoder(audio)
            if sample_rate != 16_000:
                raise TranscriptionError("Whisper requires 16 kHz audio")
            if hasattr(waveform, "detach"):
                waveform = waveform.detach().cpu().numpy()
            segments, _ = self.model.transcribe(
                waveform,
                language="ko",
                task="transcribe",
                beam_size=1,
                temperature=0,
                without_timestamps=True,
                condition_on_previous_text=False,
                max_new_tokens=self.max_new_tokens,
            )
            # Faster-Whisper's generator performs inference while iterating.
            # Consume it here, inside the inherited asyncio.to_thread boundary.
            transcript = "".join(segment.text for segment in segments).strip()
            if not transcript:
                raise TranscriptionError("transcription returned no text")
            return transcript
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError("Whisper INT8 transcription failed") from exc


def load_optimized_whisper_transcriber(model_path=None, model_factory=None):
    runtime = os.getenv("STT_RUNTIME", "faster-whisper")
    if runtime == "pytorch":
        return load_whisper_lora_transcriber()
    if runtime != "faster-whisper":
        raise STTModelLoadError(f"지원하지 않는 STT_RUNTIME: {runtime}")
    root = Path(model_path or os.getenv("STT_CT2_MODEL_PATH", DEFAULT_MODEL_PATH))
    try:
        manifest = json.loads((root / "voiceguard_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "base_model": os.getenv("STT_BASE_MODEL", BASE_MODEL),
            "adapter_model": os.getenv("STT_ADAPTER_MODEL", ADAPTER_MODEL),
            "merged": True,
            "quantization": "int8",
        }
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise ValueError("model source or conversion settings do not match")
        if not (root / "model.bin").is_file():
            raise ValueError("model.bin is missing")
        if model_factory is None:
            from faster_whisper import WhisperModel
            model_factory = WhisperModel
        model = model_factory(model_size_or_path=str(root), device="cpu", compute_type="int8")
        return CTranslateWhisperTranscriber(
            model,
            max_new_tokens=int(os.getenv("STT_MAX_NEW_TOKENS", "128")),
            chunk_seconds=float(os.getenv("STT_AUDIO_CHUNK_SECONDS", "30")),
        )
    except Exception as exc:
        raise STTModelLoadError(
            f"병합 INT8 전사 모델을 로드하지 못했습니다: {root}. "
            "tools.export_whisper_lora_ct2 명령으로 모델을 먼저 변환하세요."
        ) from exc

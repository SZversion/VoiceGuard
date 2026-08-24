import os
from collections.abc import Callable

from app.analysis.stt import FasterWhisperTranscriber


DEFAULT_MODEL_SIZE = "small"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_LANGUAGE = "ko"


class STTModelLoadError(RuntimeError):
    """Raised when the Faster-Whisper model cannot be loaded."""


def _load_model_factory() -> Callable[..., object]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise STTModelLoadError(
            "faster-whisper 의존성이 설치되지 않았습니다."
        ) from exc
    return WhisperModel


def load_stt_transcriber(
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    language: str | None = None,
    model_factory: Callable[..., object] | None = None,
) -> FasterWhisperTranscriber:
    settings = {
        "model_size_or_path": model_size or os.getenv("STT_MODEL_SIZE", DEFAULT_MODEL_SIZE),
        "device": device or os.getenv("STT_DEVICE", DEFAULT_DEVICE),
        "compute_type": compute_type or os.getenv(
            "STT_COMPUTE_TYPE",
            DEFAULT_COMPUTE_TYPE,
        ),
    }
    selected_language = language or os.getenv("STT_LANGUAGE", DEFAULT_LANGUAGE)
    factory = model_factory or _load_model_factory()

    try:
        model = factory(**settings)
    except Exception as exc:
        raise STTModelLoadError(
            f"STT 모델을 로드하지 못했습니다: {settings['model_size_or_path']}"
        ) from exc

    return FasterWhisperTranscriber(model, language=selected_language)
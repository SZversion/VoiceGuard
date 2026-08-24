import os
from collections.abc import Callable

from app.analysis.whisper_transcriber import WhisperLoRATranscriber


BASE_MODEL = "openai/whisper-small"
ADAPTER_MODEL = "VoiceGuardproject/whisper-lora-run-011"


class STTModelLoadError(RuntimeError):
    """Raised when the Whisper base model or adapter cannot be loaded."""


def _processor_factory(model_id: str):
    from transformers import WhisperProcessor

    return WhisperProcessor.from_pretrained(model_id)


def _base_model_factory(model_id: str):
    from transformers import WhisperForConditionalGeneration

    return WhisperForConditionalGeneration.from_pretrained(model_id)


def _adapter_factory(base_model, adapter_model: str):
    from peft import PeftModel

    return PeftModel.from_pretrained(base_model, adapter_model)


def load_whisper_lora_transcriber(
    base_model: str | None = None,
    adapter_model: str | None = None,
    device: str | None = None,
    processor_factory: Callable[[str], object] | None = None,
    base_model_factory: Callable[[str], object] | None = None,
    adapter_factory: Callable[[object, str], object] | None = None,
) -> WhisperLoRATranscriber:
    selected_base = base_model or os.getenv("STT_BASE_MODEL", BASE_MODEL)
    selected_adapter = adapter_model or os.getenv(
        "STT_ADAPTER_MODEL",
        ADAPTER_MODEL,
    )
    selected_device = device or os.getenv("STT_DEVICE", "cpu")

    try:
        processor = (processor_factory or _processor_factory)(selected_base)
        base = (base_model_factory or _base_model_factory)(selected_base)
        model = (adapter_factory or _adapter_factory)(base, selected_adapter)
        if hasattr(model, "to"):
            model.to(selected_device)
        if hasattr(model, "eval"):
            model.eval()
    except Exception as exc:
        raise STTModelLoadError(
            f"Whisper LoRA 모델을 로드하지 못했습니다: {selected_adapter}"
        ) from exc

    return WhisperLoRATranscriber(
        processor,
        model,
        device=selected_device,
    )
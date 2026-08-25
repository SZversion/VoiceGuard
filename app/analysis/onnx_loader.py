import os
from collections.abc import Callable

from app.analysis.model_loader import ModelLoadError
from app.analysis.onnx_classifier import OnnxTextClassifier


MODEL_ID = "user0074/voice-phishing-koelectra"
MODEL_SUBFOLDER = "koelectra_v1_onnx_int8"
MODEL_FILENAME = "model_quantized.onnx"
MAX_LENGTH = 128


def _load_dependencies():
    try:
        import onnxruntime as runtime
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise ModelLoadError(
            "onnxruntime, huggingface_hub, transformers 의존성이 설치되지 않았습니다."
        ) from exc
    return AutoTokenizer, runtime, hf_hub_download


def load_onnx_classifier(
    model_id: str = MODEL_ID,
    max_length: int = MAX_LENGTH,
    tokenizer_class=None,
    runtime_module=None,
    hub_download: Callable | None = None,
) -> OnnxTextClassifier:
    """Load the ONNX INT8 classifier and tokenizer once for application startup."""
    if tokenizer_class is None or runtime_module is None or hub_download is None:
        default_tokenizer, default_runtime, default_download = _load_dependencies()
        tokenizer_class = tokenizer_class or default_tokenizer
        runtime_module = runtime_module or default_runtime
        hub_download = hub_download or default_download

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    try:
        tokenizer = tokenizer_class.from_pretrained(
            model_id,
            subfolder=MODEL_SUBFOLDER,
            **({"token": token} if token else {}),
        )
        model_path = hub_download(
            repo_id=model_id,
            filename=f"{MODEL_SUBFOLDER}/{MODEL_FILENAME}",
            **({"token": token} if token else {}),
        )
        session = runtime_module.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
    except Exception as exc:
        raise ModelLoadError(
            f"분류모델을 로드하지 못했습니다: {model_id}/{MODEL_SUBFOLDER}"
        ) from exc

    return OnnxTextClassifier(tokenizer, session, max_length=max_length)
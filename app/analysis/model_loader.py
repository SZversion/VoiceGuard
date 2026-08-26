from collections.abc import Callable

from app.analysis.classifier import TextClassifier


MODEL_ID = "user0074/voice-phishing-koelectra"
MAX_LENGTH = 128


class ModelLoadError(RuntimeError):
    """Raised when the Hugging Face classifier cannot be loaded."""


def _load_transformers():
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise ModelLoadError(
            "transformers와 torch 의존성이 설치되지 않았습니다."
        ) from exc
    return AutoTokenizer, AutoModelForSequenceClassification


def load_text_classifier(
    model_id: str = MODEL_ID,
    max_length: int = MAX_LENGTH,
    loader: Callable | None = None,
) -> TextClassifier:
    """Load the configured Hugging Face model once for application startup."""
    load_components = loader or _load_transformers
    tokenizer_class, model_class = load_components()

    try:
        tokenizer = tokenizer_class.from_pretrained(model_id)
        model = model_class.from_pretrained(model_id)
        model.eval()
    except Exception as exc:
        raise ModelLoadError(
            f"분류모델을 로드하지 못했습니다: {model_id}"
        ) from exc

    return TextClassifier(tokenizer, model, max_length=max_length)

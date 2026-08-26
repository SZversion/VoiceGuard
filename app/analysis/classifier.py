from dataclasses import dataclass
from math import exp
from typing import Any


LABELS = {
    0: "normal",
    1: "voice_phishing",
}


@dataclass(frozen=True)
class ClassifierOutput:
    label: str
    label_id: int
    suspicion_score: float


class TextClassifier:
    """Classify a Korean transcript with an injected tokenizer and model."""

    def __init__(self, tokenizer: Any, model: Any, max_length: int = 128):
        self.tokenizer = tokenizer
        self.model = model
        self.max_length = max_length

    def classify(self, transcript: str) -> ClassifierOutput:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")

        encoded = self.tokenizer(
            transcript,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        )
        output = self.model(**encoded)
        logits = self._as_logits(output.logits)
        if len(logits) != len(LABELS):
            raise ValueError("unsupported classifier class id")

        probabilities = self._softmax(logits)
        label_id = max(range(len(probabilities)), key=probabilities.__getitem__)
        if label_id not in LABELS:
            raise ValueError("unsupported classifier class id")

        return ClassifierOutput(
            label=LABELS[label_id],
            label_id=label_id,
            suspicion_score=probabilities[1],
        )

    @staticmethod
    def _as_logits(logits: Any) -> list[float]:
        if hasattr(logits, "detach"):
            logits = logits.detach().cpu().tolist()
        if logits and isinstance(logits[0], list):
            logits = logits[0]
        return [float(value) for value in logits]

    @staticmethod
    def _softmax(logits: list[float]) -> list[float]:
        maximum = max(logits)
        exponentials = [exp(value - maximum) for value in logits]
        total = sum(exponentials)
        return [value / total for value in exponentials]

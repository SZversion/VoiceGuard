from dataclasses import dataclass
from math import exp
from typing import Any

from app.analysis.chunking import chunk_text_by_tokens


LABELS = {
    0: "normal",
    1: "voice_phishing",
}

BATCH_SIZE = 8


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
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("torch is required for PyTorch classifier inference") from exc

        with torch.inference_mode():
            output = self.model(**encoded)
        return self._result_from_logits(output.logits)

    def _result_from_logits(self, logits: Any) -> ClassifierOutput:
        logits = self._as_logits(logits)
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

    def classify_chunks(self, transcript: str) -> list[tuple[str, ClassifierOutput]]:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        chunks = chunk_text_by_tokens(transcript, self.tokenizer, self.max_length)
        if len(chunks) == 1:
            return [(chunks[0], self.classify(chunks[0]))]

        import torch

        results: list[tuple[str, ClassifierOutput]] = []
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start : start + BATCH_SIZE]
            encoded = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length,
            )
            with torch.inference_mode():
                logits = self.model(**encoded).logits
            if hasattr(logits, "detach"):
                logits = logits.detach().cpu().tolist()
            if len(logits) != len(batch):
                raise ValueError("classifier output batch size does not match input")
            results.extend(
                (chunk, self._result_from_logits(row))
                for chunk, row in zip(batch, logits)
            )
        return results

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

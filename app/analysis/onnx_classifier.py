from dataclasses import dataclass
from math import exp
from typing import Any

from app.analysis.chunking import chunk_text_by_tokens
from app.analysis.classifier import ClassifierOutput, LABELS


@dataclass(frozen=True)
class OnnxTextClassifier:
    tokenizer: Any
    session: Any
    max_length: int = 128

    def classify(self, transcript: str) -> ClassifierOutput:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")

        encoded = self.tokenizer(
            transcript,
            return_tensors="np",
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
        )
        inputs = {
            item.name: encoded[item.name]
            for item in self.session.get_inputs()
            if item.name in encoded
        }
        outputs = self.session.run(None, inputs)
        logits = self._as_logits(outputs[0])
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
        chunks = chunk_text_by_tokens(transcript, self.tokenizer, self.max_length)
        return [(chunk, self.classify(chunk)) for chunk in chunks]

    @staticmethod
    def _as_logits(logits: Any) -> list[float]:
        if hasattr(logits, "tolist"):
            logits = logits.tolist()
        if logits and isinstance(logits[0], list):
            logits = logits[0]
        return [float(value) for value in logits]

    @staticmethod
    def _softmax(logits: list[float]) -> list[float]:
        maximum = max(logits)
        exponentials = [exp(value - maximum) for value in logits]
        total = sum(exponentials)
        return [value / total for value in exponentials]
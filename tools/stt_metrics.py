"""Reference-based CER/WER metrics for Korean STT evaluation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_SPEAKER_LABEL = re.compile(r"(?:사기범|피해자)\s*:\s*")
_NOISE_MARK = re.compile(r"\([^)]*\)")


def normalize_for_metric(text: str, *, keep_spaces: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = _SPEAKER_LABEL.sub(" ", text)
    text = _NOISE_MARK.sub(" ", text)
    text = "".join(
        char if (char.isalnum() or char.isspace()) else " "
        for char in text
    )
    text = " ".join(text.split())
    return text if keep_spaces else text.replace(" ", "")


def _edit_distance(reference, hypothesis) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    reference_text = normalize_for_metric(reference)
    hypothesis_text = normalize_for_metric(hypothesis)
    if not reference_text:
        return 0.0 if not hypothesis_text else 1.0
    return _edit_distance(reference_text, hypothesis_text) / len(reference_text)


def wer(reference: str, hypothesis: str) -> float:
    reference_words = normalize_for_metric(reference, keep_spaces=True).split()
    hypothesis_words = normalize_for_metric(hypothesis, keep_spaces=True).split()
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    return _edit_distance(reference_words, hypothesis_words) / len(reference_words)


@dataclass(frozen=True)
class MetricResult:
    audio: str
    reference: str
    hypothesis: str
    cer: float
    wer: float


def evaluate_pair(audio: str, reference: str, hypothesis: str) -> MetricResult:
    return MetricResult(
        audio=audio,
        reference=reference,
        hypothesis=hypothesis,
        cer=cer(reference, hypothesis),
        wer=wer(reference, hypothesis),
    )

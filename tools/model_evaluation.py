from dataclasses import dataclass
from typing import Iterable

NORMAL = "normal"
VOICE_PHISHING = "voice_phishing"
VALID_LABELS = frozenset({NORMAL, VOICE_PHISHING})


@dataclass(frozen=True)
class EvaluationCase:
    expected_label: str
    predicted_label: str
    suspicion_score: float


def _validate_label(label: str) -> None:
    if label not in VALID_LABELS:
        raise ValueError(f"label must be one of {sorted(VALID_LABELS)}: {label}")


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def compute_metrics(cases: Iterable[EvaluationCase]) -> dict[str, float | int]:
    cases = list(cases)
    for case in cases:
        _validate_label(case.expected_label)
        _validate_label(case.predicted_label)

    true_positive = sum(
        case.expected_label == VOICE_PHISHING
        and case.predicted_label == VOICE_PHISHING
        for case in cases
    )
    true_negative = sum(
        case.expected_label == NORMAL and case.predicted_label == NORMAL
        for case in cases
    )
    false_positive = sum(
        case.expected_label == NORMAL
        and case.predicted_label == VOICE_PHISHING
        for case in cases
    )
    false_negative = sum(
        case.expected_label == VOICE_PHISHING
        and case.predicted_label == NORMAL
        for case in cases
    )

    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)

    return {
        "total": len(cases),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "accuracy": _ratio(true_positive + true_negative, len(cases)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": _ratio(false_positive, false_positive + true_negative),
    }
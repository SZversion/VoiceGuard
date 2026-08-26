"""Evaluate domain correction impact without persisting transcript contents."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from app.analysis.domain_corrector import DomainTermCorrector
from tools.stt_metrics import cer, wer


def evaluate_pairs(
    pairs: Iterable[Mapping[str, str]],
    corrector: DomainTermCorrector,
) -> dict[str, Any]:
    """Return aggregate metrics and rule-level impact for reference/hypothesis pairs."""

    rows = []
    rule_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "application_count": 0,
            "sample_count": 0,
            "improved_sample_count": 0,
            "worsened_sample_count": 0,
            "unchanged_sample_count": 0,
        }
    )

    for pair in pairs:
        sample_id = pair.get("sample_id", "")
        reference = pair.get("reference", "")
        hypothesis = pair.get("hypothesis", "")
        if not sample_id or not reference or not hypothesis:
            raise ValueError("sample_id, reference, and hypothesis are required")

        correction = corrector.correct(hypothesis)
        raw_cer = cer(reference, hypothesis)
        corrected_cer = cer(reference, correction.corrected_transcript)
        raw_wer = wer(reference, hypothesis)
        corrected_wer = wer(reference, correction.corrected_transcript)
        cer_delta = corrected_cer - raw_cer
        wer_delta = corrected_wer - raw_wer
        rows.append(
            (
                raw_cer,
                corrected_cer,
                raw_wer,
                corrected_wer,
                bool(correction.corrections),
            )
        )

        for applied in correction.corrections:
            stats = rule_stats[applied.rule_id]
            stats["application_count"] += 1
            stats["sample_count"] += 1
            if cer_delta < 0 or wer_delta < 0:
                stats["improved_sample_count"] += 1
            elif cer_delta > 0 or wer_delta > 0:
                stats["worsened_sample_count"] += 1
            else:
                stats["unchanged_sample_count"] += 1

    if not rows:
        raise ValueError("at least one evaluation pair is required")

    return {
        "sample_count": len(rows),
        "changed_sample_count": sum(row[4] for row in rows),
        "average_raw_cer": _average(0, rows),
        "average_corrected_cer": _average(1, rows),
        "average_raw_wer": _average(2, rows),
        "average_corrected_wer": _average(3, rows),
        "cer_delta": sum(row[1] - row[0] for row in rows) / len(rows),
        "wer_delta": sum(row[3] - row[2] for row in rows) / len(rows),
        "rules": dict(rule_stats),
    }


def _average(index: int, rows: list[tuple[float, float, float, float, bool]]) -> float:
    return sum(row[index] for row in rows) / len(rows)

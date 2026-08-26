"""Resumable raw-vs-corrected classifier evaluation for paired audio datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.analysis.classifier import TextClassifier
from app.analysis.domain_corrector import DomainTermCorrector, load_default_domain_rules


def _new_state() -> dict:
    return {
        "processed_ids": [],
        "sample_count": 0,
        "changed_transcript_count": 0,
        "changed_prediction_count": 0,
        "raw": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "corrected": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "rules": {},
    }


def _update_confusion(bucket: dict, actual: bool, predicted: bool) -> None:
    if actual and predicted:
        bucket["tp"] += 1
    elif not actual and not predicted:
        bucket["tn"] += 1
    elif not actual and predicted:
        bucket["fp"] += 1
    else:
        bucket["fn"] += 1


def _metrics(bucket: dict) -> dict:
    tp, tn, fp, fn = (bucket[key] for key in ("tp", "tn", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / (tp + tn + fp + fn) if tp + tn + fp + fn else 0.0,
        "precision": precision,
        "recall": recall,
        "fnr": fn / (tp + fn) if tp + fn else 0.0,
        "fpr": fp / (tn + fp) if tn + fp else 0.0,
        "f1": f1,
        "confusion": dict(bucket),
    }


def _summary(state: dict) -> dict:
    return {
        "sample_count": state["sample_count"],
        "changed_transcript_count": state["changed_transcript_count"],
        "changed_prediction_count": state["changed_prediction_count"],
        "raw": _metrics(state["raw"]),
        "corrected": _metrics(state["corrected"]),
        "rules": state["rules"],
    }


def _update(
    state: dict,
    sample_id: str,
    actual: bool,
    raw_label: bool,
    corrected_label: bool,
    correction_ids: list[str],
) -> None:
    state["processed_ids"].append(sample_id)
    state["sample_count"] += 1
    state["changed_transcript_count"] += bool(correction_ids)
    state["changed_prediction_count"] += raw_label != corrected_label
    _update_confusion(state["raw"], actual, raw_label)
    _update_confusion(state["corrected"], actual, corrected_label)
    for rule_id in correction_ids:
        state["rules"].setdefault(rule_id, 0)
        state["rules"][rule_id] += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--model-id", default="user0074/voice-phishing-koelectra")
    args = parser.parse_args()

    state = _new_state()
    if args.checkpoint.exists():
        state = json.loads(args.checkpoint.read_text(encoding="utf-8"))

    audios = sorted(
        (
            audio
            for group in ("negative", "positive")
            for audio in (args.root / group / "audio").glob("*.wav")
            if (audio.parent.parent / "labels" / f"{audio.stem}.txt").exists()
        ),
        key=lambda path: path.name,
    )

    from faster_whisper import WhisperModel

    stt_model = WhisperModel("small", device="cuda", compute_type="float16")
    classifier = TextClassifier(*_load_classifier_components(args.model_id))
    corrector = DomainTermCorrector(load_default_domain_rules())
    processed = set(state["processed_ids"])

    for audio in audios:
        if audio.stem in processed:
            continue
        segments, _ = stt_model.transcribe(
            str(audio), language="ko", beam_size=5, vad_filter=True, word_timestamps=False
        )
        raw_transcript = " ".join(str(segment.text).strip() for segment in segments).strip()
        if not raw_transcript:
            continue
        corrected = corrector.correct(raw_transcript)
        actual = audio.parent.parent.name == "positive"
        raw_prediction = classifier.classify(raw_transcript).label_id == 1
        corrected_prediction = classifier.classify(corrected.corrected_transcript).label_id == 1
        _update(
            state,
            audio.stem,
            actual,
            raw_prediction,
            corrected_prediction,
            [item.rule_id for item in corrected.corrections],
        )
        if state["sample_count"] % args.save_every == 0:
            args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
            args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{state['sample_count']}/{len(audios)}] {audio.stem}", flush=True)

    args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(_summary(state), ensure_ascii=False, indent=2), flush=True)
    return 0


def _load_classifier_components(model_id: str):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    model.eval()
    return tokenizer, model


if __name__ == "__main__":
    raise SystemExit(main())

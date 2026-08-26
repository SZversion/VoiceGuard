"""Resumable GPU evaluation for paired audio/reference datasets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.analysis.domain_corrector import DomainTermCorrector, load_default_domain_rules
from tools.stt_metrics import cer, wer


def _new_state() -> dict:
    return {
        "processed_ids": [],
        "sample_count": 0,
        "changed_sample_count": 0,
        "raw_cer_sum": 0.0,
        "corrected_cer_sum": 0.0,
        "raw_wer_sum": 0.0,
        "corrected_wer_sum": 0.0,
        "rules": {},
    }


def _update(state: dict, sample_id: str, reference: str, hypothesis: str, corrector: DomainTermCorrector) -> None:
    result = corrector.correct(hypothesis)
    raw_cer = cer(reference, hypothesis)
    corrected_cer = cer(reference, result.corrected_transcript)
    raw_wer = wer(reference, hypothesis)
    corrected_wer = wer(reference, result.corrected_transcript)
    state["processed_ids"].append(sample_id)
    state["sample_count"] += 1
    state["changed_sample_count"] += bool(result.corrections)
    state["raw_cer_sum"] += raw_cer
    state["corrected_cer_sum"] += corrected_cer
    state["raw_wer_sum"] += raw_wer
    state["corrected_wer_sum"] += corrected_wer
    for item in result.corrections:
        stats = state["rules"].setdefault(item.rule_id, {"application_count": 0, "improved_sample_count": 0, "worsened_sample_count": 0, "unchanged_sample_count": 0})
        stats["application_count"] += 1
        if corrected_cer < raw_cer or corrected_wer < raw_wer:
            stats["improved_sample_count"] += 1
        elif corrected_cer > raw_cer or corrected_wer > raw_wer:
            stats["worsened_sample_count"] += 1
        else:
            stats["unchanged_sample_count"] += 1


def _summary(state: dict) -> dict:
    count = state["sample_count"]
    return {
        "sample_count": count,
        "changed_sample_count": state["changed_sample_count"],
        "average_raw_cer": state["raw_cer_sum"] / count if count else None,
        "average_corrected_cer": state["corrected_cer_sum"] / count if count else None,
        "average_raw_wer": state["raw_wer_sum"] / count if count else None,
        "average_corrected_wer": state["corrected_wer_sum"] / count if count else None,
        "cer_delta": (state["corrected_cer_sum"] - state["raw_cer_sum"]) / count if count else None,
        "wer_delta": (state["corrected_wer_sum"] - state["raw_wer_sum"]) / count if count else None,
        "rules": state["rules"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--save-every", type=int, default=10)
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

    model = WhisperModel("small", device="cuda", compute_type="float16")
    corrector = DomainTermCorrector(load_default_domain_rules())
    processed = set(state["processed_ids"])
    for index, audio in enumerate(audios, 1):
        if audio.stem in processed:
            continue
        segments, _ = model.transcribe(str(audio), language="ko", beam_size=5, vad_filter=True, word_timestamps=False)
        hypothesis = " ".join(str(segment.text).strip() for segment in segments).strip()
        reference = (audio.parent.parent / "labels" / f"{audio.stem}.txt").read_text(encoding="utf-8")
        _update(state, audio.stem, reference, hypothesis, corrector)
        if state["sample_count"] % args.save_every == 0:
            args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
            args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{state['sample_count']}/{len(audios)}] {audio.stem}", flush=True)
    args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(_summary(state), ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

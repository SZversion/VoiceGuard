"""Add duration-matched, call-merged negative data from a chunked WAV/TXT corpus."""

from __future__ import annotations

import argparse
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tools.prepare_stt_dataset import SAMPLE_RATE, decode_audio, read_text, write_wav


@dataclass(frozen=True)
class CallInfo:
    call_id: str
    audio_files: tuple[Path, ...]
    label_files: tuple[Path, ...]
    duration: float


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def discover_calls(
    audio_root: Path,
    label_root: Path,
    stop_after_seconds: float | None = None,
) -> tuple[list[CallInfo], list[dict[str, str]]]:
    calls: list[CallInfo] = []
    issues: list[dict[str, str]] = []
    accumulated_seconds = 0.0
    for call_dir in sorted(audio_root.iterdir()):
        if not call_dir.is_dir():
            continue
        label_dir = label_root / call_dir.name
        if not label_dir.is_dir():
            issues.append({"call": call_dir.name, "reason": "missing_label_directory"})
            continue
        audio_files = tuple(sorted(call_dir.glob("*.wav")))
        label_files: list[Path] = []
        valid_audio: list[Path] = []
        for audio in audio_files:
            label = label_dir / f"{audio.stem}.txt"
            if not label.exists():
                issues.append({"call": call_dir.name, "file": audio.name, "reason": "missing_label"})
                continue
            valid_audio.append(audio)
            label_files.append(label)
        if not valid_audio:
            issues.append({"call": call_dir.name, "reason": "no_valid_pairs"})
            continue
        call = CallInfo(
            call_id=call_dir.name,
            audio_files=tuple(valid_audio),
            label_files=tuple(label_files),
            duration=sum(wav_duration(path) for path in valid_audio),
        )
        calls.append(call)
        accumulated_seconds += call.duration
        if stop_after_seconds is not None and accumulated_seconds >= stop_after_seconds:
            break
    return calls, issues


def select_calls(calls: list[CallInfo], target_seconds: float) -> list[CallInfo]:
    selected: list[CallInfo] = []
    remaining = max(0.0, target_seconds)
    for call in sorted(calls, key=lambda item: item.duration, reverse=True):
        if call.duration <= remaining:
            selected.append(call)
            remaining -= call.duration
        if remaining <= 1.0:
            break
    if remaining > 1.0:
        unused = [call for call in calls if call not in selected]
        if unused:
            closest = min(unused, key=lambda item: abs(item.duration - remaining))
            selected.append(closest)
    return selected


def merge_call(call: CallInfo) -> tuple[np.ndarray, str]:
    audio_parts = [decode_audio(path) for path in call.audio_files]
    silence = np.zeros(round(SAMPLE_RATE * 0.2), dtype=np.float32)
    merged_audio = np.concatenate(
        [part for index, part in enumerate(audio_parts) for part in (([part, silence] if index < len(audio_parts) - 1 else [part]))]
    )
    text_parts = []
    for path in call.label_files:
        text = read_text(path)
        if text:
            text_parts.append(text)
    transcript = " ".join(text_parts)
    return merged_audio, transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add call-merged negative audio until a target duration is reached")
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--additional-audio-root", type=Path, required=True)
    parser.add_argument("--additional-label-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary_path = args.prepared_root / "summary.json"
    manifest_path = args.prepared_root / "manifest.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    target_seconds = max(0.0, float(summary["positive_duration_seconds"]) - float(summary["negative_duration_seconds"]))
    calls, issues = discover_calls(
        args.additional_audio_root,
        args.additional_label_root,
        stop_after_seconds=target_seconds,
    )
    selected = select_calls(calls, target_seconds)
    selection = {
        "target_seconds": target_seconds,
        "available_calls": len(calls),
        "selected_calls": len(selected),
        "selected_seconds_before_resample": sum(item.duration for item in selected),
        "issues": issues,
        "calls": [{"id": item.call_id, "duration_seconds": item.duration} for item in selected],
    }
    print(json.dumps(selection, ensure_ascii=False))
    if args.dry_run:
        return 0

    records = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    existing_ids = {record["id"] for record in records}
    added_records: list[dict[str, Any]] = []
    for call in selected:
        output_id = f"D03_J13_{call.call_id}"
        if output_id in existing_ids:
            continue
        merged_audio, transcript = merge_call(call)
        audio_path = args.prepared_root / "negative" / "audio" / f"{output_id}.wav"
        text_path = args.prepared_root / "negative" / "labels" / f"{output_id}.txt"
        write_wav(audio_path, merged_audio)
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(transcript + "\n", encoding="utf-8")
        added_records.append({
            "id": output_id,
            "label": "negative",
            "audio": str(audio_path),
            "text": str(text_path),
            "source_audio_call": str(call.audio_files[0].parent),
            "source_label_call": str(call.label_files[0].parent),
            "dialog_count": len(call.audio_files),
            "duration_seconds": len(merged_audio) / SAMPLE_RATE,
            "source_dataset": "D03/J13",
        })

    records.extend(added_records)
    manifest_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    summary["negative_duration_seconds"] = sum(record["duration_seconds"] for record in records if record["label"] == "negative")
    summary["negative_call_count"] = sum(1 for record in records if record["label"] == "negative")
    summary["negative_added_from_d03_j13"] = len(added_records)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.prepared_root / "d03_j13_selection.json").write_text(
        json.dumps({**selection, "added_records": added_records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

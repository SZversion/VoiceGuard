"""Prepare positive/negative Korean ASR data without modifying source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


SAMPLE_RATE = 16_000
MARKER_RE = re.compile(r"\(삐-\)")


@dataclass
class PositiveItem:
    audio: Path
    text: Path
    output_id: str
    duration: float = 0.0
    beep_count_expected: int = 0
    beep_count_detected: int = 0
    beep_intervals: list[dict[str, float]] | None = None


@dataclass
class NegativeCall:
    call_id: str
    audio_files: list[Path]
    text_files: list[Path]
    transcript: str
    duration: float


def decode_audio(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Decode common audio formats to mono float32 at the target sample rate."""
    try:
        import av
    except ImportError as error:
        raise RuntimeError("PyAV is required. Install it with: python -m pip install av") from error

    container = av.open(str(path))
    stream = next((item for item in container.streams if item.type == "audio"), None)
    if stream is None:
        container.close()
        raise ValueError(f"No audio stream found: {path}")

    resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=sample_rate)
    chunks: list[np.ndarray] = []
    decode_error: Exception | None = None
    try:
        for frame in container.decode(stream):
            converted = resampler.resample(frame)
            if not isinstance(converted, list):
                converted = [converted]
            chunks.extend(item.to_ndarray().reshape(-1) for item in converted)
        try:
            converted = resampler.resample(None)
            if not isinstance(converted, list):
                converted = [converted]
            chunks.extend(item.to_ndarray().reshape(-1) for item in converted if item is not None)
        except Exception as error:
            decode_error = error
    except Exception as error:
        decode_error = error
    finally:
        container.close()

    if not chunks:
        raise ValueError(f"Audio stream contains no samples: {path}")
    if decode_error is not None:
        print(f"WARNING partial audio decode: {path.name}: {decode_error}")
    return np.concatenate(chunks).astype(np.float32, copy=False)


def write_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).round().astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def remove_beep_markers(text: str) -> str:
    cleaned = MARKER_RE.sub(" ", text)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def detect_beeps(
    audio: np.ndarray,
    sample_rate: int,
    expected_count: int,
    min_frequency: float = 500.0,
    max_frequency: float = 3_000.0,
) -> list[tuple[int, int, float]]:
    """Detect tonal beep candidates and select at most expected_count events."""
    if expected_count <= 0:
        return []
    frame_size = max(256, round(sample_rate * 0.02))
    hop = max(128, round(sample_rate * 0.01))
    if len(audio) < frame_size:
        return []

    window = np.hanning(frame_size)
    frequencies = np.fft.rfftfreq(frame_size, 1.0 / sample_rate)
    band = (frequencies >= min_frequency) & (frequencies <= max_frequency)
    candidates: list[tuple[int, float]] = []
    for start in range(0, len(audio) - frame_size + 1, hop):
        frame = audio[start : start + frame_size]
        rms = float(np.sqrt(np.mean(np.square(frame))))
        if rms < 10 ** (-55 / 20):
            continue
        power = np.abs(np.fft.rfft(frame * window)) ** 2
        band_power = power[band]
        if not len(band_power) or float(band_power.sum()) <= 0:
            continue
        peak_ratio = float(band_power.max() / band_power.sum())
        if peak_ratio >= 0.42:
            candidates.append((start, peak_ratio))

    groups: list[tuple[int, int, float]] = []
    max_gap = hop * 3
    for start, score in candidates:
        if not groups or start - groups[-1][1] > max_gap:
            groups.append((start, start + frame_size, score))
        else:
            old_start, old_end, old_score = groups[-1]
            groups[-1] = (old_start, start + frame_size, max(old_score, score))

    groups = [item for item in groups if 0.08 <= (item[1] - item[0]) / sample_rate <= 1.5]
    selected: list[tuple[int, int, float]] = []
    for candidate in sorted(groups, key=lambda item: item[2], reverse=True):
        if any(candidate[0] < item[1] and item[0] < candidate[1] for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= expected_count:
            break
    return sorted(selected)


def remove_intervals(audio: np.ndarray, intervals: list[tuple[int, int, float]]) -> np.ndarray:
    if not intervals:
        return audio
    pieces: list[np.ndarray] = []
    cursor = 0
    for start, end, _ in intervals:
        start = max(cursor, min(start, len(audio)))
        end = max(start, min(end, len(audio)))
        pieces.append(audio[cursor:start])
        cursor = end
    pieces.append(audio[cursor:])
    return np.concatenate([piece for piece in pieces if len(piece)])


def stable_output_id(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("").as_posix()
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:10]
    stem = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", path.stem).strip("_")[:80]
    return f"{stem}_{digest}"


def positive_items(root: Path) -> list[PositiveItem]:
    items: list[PositiveItem] = []
    for audio in sorted(root.rglob("*.mp3")):
        text = audio.with_suffix(".txt")
        if text.exists():
            items.append(
                PositiveItem(
                    audio=audio,
                    text=text,
                    output_id=stable_output_id(audio, root),
                    beep_count_expected=len(MARKER_RE.findall(read_text(text))),
                )
            )
    return items


def load_negative_call(audio_dir: Path, label_dir: Path, call_id: str) -> NegativeCall:
    metadata_path = label_dir / call_id / f"{call_id}.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing call metadata: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    dialogs = metadata.get("dataSet", {}).get("dialogs", [])
    audio_files: list[Path] = []
    text_files: list[Path] = []
    audio_parts: list[np.ndarray] = []
    text_parts: list[str] = []
    for dialog in dialogs:
        audio_name = Path(dialog["audioPath"]).name
        text_name = Path(dialog["textPath"]).name
        audio_path = audio_dir / call_id / audio_name
        text_path = label_dir / call_id / text_name
        if not audio_path.exists() or not text_path.exists():
            continue
        audio_files.append(audio_path)
        text_files.append(text_path)
        audio_parts.append(decode_audio(audio_path))
        text_parts.append(read_text(text_path))

    if not audio_parts:
        raise ValueError(f"No valid dialog pairs: {call_id}")
    silence = np.zeros(round(SAMPLE_RATE * 0.2), dtype=np.float32)
    merged_audio = np.concatenate(
        [part for index, part in enumerate(audio_parts) for part in (([part, silence] if index < len(audio_parts) - 1 else [part]))]
    )
    return NegativeCall(
        call_id=call_id,
        audio_files=audio_files,
        text_files=text_files,
        transcript=" ".join(part for part in text_parts if part),
        duration=len(merged_audio) / SAMPLE_RATE,
    )


def select_negative_calls(calls: list[NegativeCall], target_duration: float, seed: int) -> list[NegativeCall]:
    rng = np.random.default_rng(seed)
    shuffled = list(calls)
    rng.shuffle(shuffled)
    ordered = sorted(shuffled, key=lambda item: item.duration, reverse=True)
    selected: list[NegativeCall] = []
    remaining = target_duration
    for call in ordered:
        if call.duration <= remaining or not selected:
            selected.append(call)
            remaining -= call.duration
        if remaining <= 0:
            break
    if remaining > 0 and len(selected) < len(ordered):
        closest = min(ordered, key=lambda item: abs(item.duration - remaining))
        if closest not in selected:
            selected.append(closest)
    return selected


def prepare_positive(items: list[PositiveItem], output: Path) -> tuple[float, list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    total_duration = 0.0
    for item in items:
        text = read_text(item.text)
        audio = decode_audio(item.audio)
        intervals = detect_beeps(audio, SAMPLE_RATE, item.beep_count_expected)
        item.beep_count_detected = len(intervals)
        item.beep_intervals = [
            {"start": start / SAMPLE_RATE, "end": end / SAMPLE_RATE, "score": score}
            for start, end, score in intervals
        ]
        if item.beep_count_detected != item.beep_count_expected:
            print(f"WARNING beep count mismatch: {item.audio.name}: expected={item.beep_count_expected}, detected={item.beep_count_detected}")
            cleaned_audio = audio
        else:
            cleaned_audio = remove_intervals(audio, intervals)
        cleaned_text = remove_beep_markers(text)
        output_audio = output / "audio" / f"{item.output_id}.wav"
        output_text = output / "labels" / f"{item.output_id}.txt"
        write_wav(output_audio, cleaned_audio)
        output_text.parent.mkdir(parents=True, exist_ok=True)
        output_text.write_text(cleaned_text + "\n", encoding="utf-8")
        duration = len(cleaned_audio) / SAMPLE_RATE
        total_duration += duration
        manifest.append({
            "id": item.output_id,
            "label": "positive",
            "audio": str(output_audio),
            "text": str(output_text),
            "source_audio": str(item.audio),
            "source_text": str(item.text),
            "duration_seconds": duration,
            "beep_expected": item.beep_count_expected,
            "beep_detected": item.beep_count_detected,
            "beep_intervals": item.beep_intervals,
        })
    return total_duration, manifest


def prepare_negative(calls: list[NegativeCall], output: Path) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for call in calls:
        audio_parts = [decode_audio(path) for path in call.audio_files]
        silence = np.zeros(round(SAMPLE_RATE * 0.2), dtype=np.float32)
        merged = np.concatenate(
            [part for index, part in enumerate(audio_parts) for part in (([part, silence] if index < len(audio_parts) - 1 else [part]))]
        )
        output_audio = output / "audio" / f"{call.call_id}.wav"
        output_text = output / "labels" / f"{call.call_id}.txt"
        write_wav(output_audio, merged)
        output_text.parent.mkdir(parents=True, exist_ok=True)
        output_text.write_text(call.transcript + "\n", encoding="utf-8")
        manifest.append({
            "id": call.call_id,
            "label": "negative",
            "audio": str(output_audio),
            "text": str(output_text),
            "source_audio_call": str(call.audio_files[0].parent),
            "source_label_call": str(call.text_files[0].parent),
            "dialog_count": len(call.audio_files),
            "duration_seconds": len(merged) / SAMPLE_RATE,
        })
    return manifest


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare matched positive/negative Korean ASR data")
    parser.add_argument("--positive-root", type=Path, required=True)
    parser.add_argument("--negative-audio-root", type=Path, required=True)
    parser.add_argument("--negative-label-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    items = positive_items(args.positive_root)
    if not items:
        raise ValueError("No positive MP3/TXT pairs found")
    positive_duration = 0.0
    positive_manifest: list[dict[str, Any]] = []
    if not args.dry_run:
        positive_duration, positive_manifest = prepare_positive(items, args.output / "positive")
    else:
        for item in items:
            positive_duration += len(decode_audio(item.audio)) / SAMPLE_RATE

    calls: list[NegativeCall] = []
    for directory in sorted(args.negative_audio_root.iterdir()):
        if directory.is_dir() and (args.negative_label_root / directory.name).is_dir():
            calls.append(load_negative_call(args.negative_audio_root, args.negative_label_root, directory.name))
    selected = select_negative_calls(calls, positive_duration, args.seed)
    print(json.dumps({
        "positive_items": len(items),
        "positive_duration_seconds": positive_duration,
        "negative_calls_available": len(calls),
        "negative_calls_selected": len(selected),
        "negative_duration_seconds": sum(item.duration for item in selected),
        "dry_run": args.dry_run,
    }, ensure_ascii=False))
    if args.dry_run:
        return 0

    negative_manifest = prepare_negative(selected, args.output / "negative")
    all_manifest = positive_manifest + negative_manifest
    write_jsonl(args.output / "manifest.jsonl", all_manifest)
    (args.output / "beep_events.json").write_text(
        json.dumps([item for item in positive_manifest if item["beep_expected"]], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "summary.json").write_text(
        json.dumps({
            "positive_duration_seconds": positive_duration,
            "negative_duration_seconds": sum(item["duration_seconds"] for item in negative_manifest),
            "positive_count": len(positive_manifest),
            "negative_call_count": len(negative_manifest),
            "sample_rate": SAMPLE_RATE,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

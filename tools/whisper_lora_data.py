"""Discover and split same-directory audio/TXT pairs for Whisper training."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from tools.transcript_cleaning import clean_training_text


@dataclass(frozen=True)
class AudioTextPair:
    audio: Path
    text: Path
    transcript: str

    @property
    def identifier(self) -> str:
        return self.audio.with_suffix("").as_posix()


def source_group_identifier(pair: AudioTextPair) -> str:
    """Return the original-call identifier shared by overlapping chunks."""
    stem = pair.audio.stem
    if "__chunk_" in stem:
        return stem.split("__chunk_", 1)[0]
    match = re.match(r"^(PHISH_\d+)_\d{4}$", stem, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.match(r"^(.+?)__\d{4}$", stem)
    if match:
        return match.group(1)
    return stem


@dataclass(frozen=True)
class DataIssue:
    code: str
    path: Path
    message: str


@dataclass(frozen=True)
class SplitRatios:
    train: float
    validation: float
    test: float

    def __post_init__(self) -> None:
        values = (self.train, self.validation, self.test)
        if any(value <= 0 for value in values):
            raise ValueError("split ratios must be positive")
        if abs(sum(values) - 1.0) > 1e-6:
            raise ValueError("split ratios must sum to 1.0")


def discover_pairs(
    root: Path,
    extensions: tuple[str, ...],
    *,
    clean_transcripts: bool = False,
    min_transcript_chars: int = 1,
) -> tuple[list[AudioTextPair], list[DataIssue]]:
    """Find valid sibling audio/TXT pairs and report invalid audio files."""
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    if min_transcript_chars < 1:
        raise ValueError("min_transcript_chars must be at least 1")

    normalized_extensions = {extension.lower() for extension in extensions}
    pairs: list[AudioTextPair] = []
    issues: list[DataIssue] = []
    seen_identifiers: set[str] = set()

    files = sorted(root.rglob("*"))
    text_files = {
        (path.parent, path.stem.casefold()): path
        for path in files
        if path.is_file() and path.suffix.lower() == ".txt"
    }

    for audio in files:
        if not audio.is_file() or audio.suffix.lower() not in normalized_extensions:
            continue

        text = text_files.get((audio.parent, audio.stem.casefold()))
        if text is None:
            issues.append(DataIssue("missing_text", audio, f"No sibling TXT found for {audio.name}"))
            continue

        identifier = audio.with_suffix("").relative_to(root).as_posix()
        if identifier in seen_identifiers:
            issues.append(DataIssue("duplicate_pair", audio, f"Duplicate identifier: {identifier}"))
            continue

        try:
            transcript = text.read_text(encoding="utf-8").strip()
        except UnicodeError as error:
            issues.append(DataIssue("invalid_text_encoding", text, str(error)))
            continue

        if not transcript:
            issues.append(DataIssue("empty_text", text, "TXT transcript is empty"))
            continue

        if clean_transcripts:
            transcript = clean_training_text(transcript)
        if len(transcript) < min_transcript_chars:
            issues.append(
                DataIssue(
                    "short_text",
                    text,
                    f"Transcript has {len(transcript)} characters; minimum is {min_transcript_chars}",
                )
            )
            continue

        seen_identifiers.add(identifier)
        pairs.append(AudioTextPair(audio=audio, text=text, transcript=transcript))

    return pairs, issues


def _split_counts(total: int, ratios: SplitRatios) -> tuple[int, int, int]:
    if total < 3:
        raise ValueError("at least 3 valid pairs are required for train/validation/test")

    raw = [total * ratios.train, total * ratios.validation, total * ratios.test]
    counts = [max(1, int(value)) for value in raw]
    while sum(counts) > total:
        index = max(range(3), key=lambda item: (counts[item] - raw[item], counts[item]))
        if counts[index] > 1:
            counts[index] -= 1
        else:
            break
    while sum(counts) < total:
        index = max(range(3), key=lambda item: raw[item] - counts[item])
        counts[index] += 1
    return counts[0], counts[1], counts[2]


def split_pairs(pairs: list[AudioTextPair], ratios: SplitRatios, seed: int) -> dict[str, list[AudioTextPair]]:
    """Deterministically split pairs without overlap."""
    shuffled = list(pairs)
    random.Random(seed).shuffle(shuffled)
    train_count, validation_count, _ = _split_counts(len(shuffled), ratios)
    return {
        "train": shuffled[:train_count],
        "validation": shuffled[train_count : train_count + validation_count],
        "test": shuffled[train_count + validation_count :],
    }


def split_pairs_by_source(pairs: list[AudioTextPair], ratios: SplitRatios, seed: int) -> dict[str, list[AudioTextPair]]:
    """Split whole original sources so overlapping chunks never cross splits."""
    if len(pairs) < 3:
        raise ValueError("at least 3 valid pairs are required for train/validation/test")
    grouped: dict[str, list[AudioTextPair]] = {}
    for pair in pairs:
        grouped.setdefault(source_group_identifier(pair), []).append(pair)
    if len(grouped) < 3:
        raise ValueError("at least 3 source groups are required for grouped splitting")

    groups = list(grouped.items())
    random.Random(seed).shuffle(groups)
    targets = [len(pairs) * ratios.train, len(pairs) * ratios.validation, len(pairs) * ratios.test]
    assigned: list[list[AudioTextPair]] = [[], [], []]
    for index, (_, group_pairs) in enumerate(groups):
        if index < 3:
            split_index = index
        else:
            split_index = min(range(3), key=lambda candidate: len(assigned[candidate]) / max(targets[candidate], 1.0))
        assigned[split_index].extend(group_pairs)
    return {"train": assigned[0], "validation": assigned[1], "test": assigned[2]}


def write_manifest(splits: dict[str, list[AudioTextPair]], path: Path) -> None:
    """Write one JSON object per pair, including its split."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for split in ("train", "validation", "test"):
            for pair in splits.get(split, []):
                handle.write(
                    json.dumps(
                        {
                            "split": split,
                            "identifier": pair.identifier,
                            "source_group": source_group_identifier(pair),
                            "audio": str(pair.audio),
                            "text": str(pair.text),
                            "transcript": pair.transcript,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

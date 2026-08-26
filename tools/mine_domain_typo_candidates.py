"""Mine domain-token substitution candidates without storing transcripts."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import Counter
from pathlib import Path


DOMAIN_TERMS = ("보이스", "피싱", "피시", "대포", "검찰", "명의", "개인", "금융", "대출", "수사", "계좌", "통장")


def tokens(text: str) -> list[str]:
    return re.findall(r"[가-힣A-Za-z0-9]+", text)


def update_candidates(counter: Counter[tuple[str, str]], reference: str, hypothesis: str) -> None:
    ref = tokens(reference)
    hyp = tokens(hypothesis)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ref, b=hyp).get_opcodes():
        if tag != "replace" or i2 - i1 != 1 or j2 - j1 != 1:
            continue
        source, target = ref[i1], hyp[j1]
        if any(term in source or term in target for term in DOMAIN_TERMS):
            counter[(source, target)] += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()
    state = {"processed_ids": [], "candidate_counts": {}}
    if args.checkpoint.exists():
        state = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    counts = Counter({tuple(key.split("\t", 1)): value for key, value in state["candidate_counts"].items()})
    processed = set(state["processed_ids"])
    audios = sorted((audio for group in ("negative", "positive") for audio in (args.root / group / "audio").glob("*.wav") if (audio.parent.parent / "labels" / f"{audio.stem}.txt").exists()), key=lambda p: p.name)
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cuda", compute_type="float16")
    for index, audio in enumerate(audios, 1):
        if audio.stem in processed:
            continue
        segments, _ = model.transcribe(str(audio), language="ko", beam_size=5, vad_filter=True, word_timestamps=False)
        hypothesis = " ".join(str(segment.text).strip() for segment in segments).strip()
        reference = (audio.parent.parent / "labels" / f"{audio.stem}.txt").read_text(encoding="utf-8")
        update_candidates(counts, reference, hypothesis)
        processed.add(audio.stem)
        state = {"processed_ids": sorted(processed), "candidate_counts": {f"{a}\t{b}": n for (a, b), n in counts.items()}}
        if len(processed) % 10 == 0:
            args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
            args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{len(processed)}/{len(audios)}] {audio.stem}", flush=True)
    args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(sorted(({"source": a, "target": b, "count": n} for (a, b), n in counts.items()), key=lambda row: (-row["count"], row["source"], row["target"])), ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

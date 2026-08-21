import json
import tempfile
import unittest
from pathlib import Path

from tools.whisper_lora_data import (
    AudioTextPair,
    SplitRatios,
    discover_pairs,
    split_pairs,
    split_pairs_by_source,
    source_group_identifier,
    write_manifest,
)


def make_pairs(root: Path, count: int) -> list[AudioTextPair]:
    pairs = []
    for index in range(count):
        audio = root / f"sample_{index}.wav"
        text = root / f"sample_{index}.txt"
        pairs.append(AudioTextPair(audio=audio, text=text, transcript=f"문장 {index}"))
    return pairs


class WhisperLoraDataTests(unittest.TestCase):
    def test_discover_pairs_matches_same_stem_in_same_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "sample.wav"
            label = root / "sample.txt"
            audio.write_bytes(b"audio")
            label.write_text("안녕하세요", encoding="utf-8")

            pairs, issues = discover_pairs(root, (".wav",))

            self.assertEqual([(item.audio.name, item.text.name) for item in pairs], [("sample.wav", "sample.txt")])
            self.assertEqual(issues, [])

    def test_missing_text_is_reported_and_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.wav").write_bytes(b"audio")

            pairs, issues = discover_pairs(root, (".wav",))

            self.assertEqual(pairs, [])
            self.assertEqual(issues[0].code, "missing_text")

    def test_discover_pairs_supports_mirrored_label_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio_root = root / "audio"
            label_root = root / "labels"
            (audio_root / "loanScam").mkdir(parents=True)
            (label_root / "loanScam").mkdir(parents=True)
            (audio_root / "loanScam" / "chunk_0001.wav").write_bytes(b"audio")
            (label_root / "loanScam" / "chunk_0001.txt").write_text("라벨", encoding="utf-8")

            pairs, issues = discover_pairs(audio_root, (".wav",), text_root=label_root)

            self.assertEqual([(item.audio.name, item.text.name) for item in pairs], [("chunk_0001.wav", "chunk_0001.txt")])
            self.assertEqual(issues, [])

    def test_split_pairs_has_no_overlap_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            pairs = make_pairs(Path(directory), count=10)

            first = split_pairs(pairs, SplitRatios(0.8, 0.1, 0.1), seed=42)
            second = split_pairs(pairs, SplitRatios(0.8, 0.1, 0.1), seed=42)

            first_ids = {key: {item.identifier for item in value} for key, value in first.items()}
            self.assertTrue(first_ids["train"].isdisjoint(first_ids["validation"]))
            self.assertTrue(first_ids["train"].isdisjoint(first_ids["test"]))
            self.assertEqual(first, second)

    def test_write_manifest_writes_split_and_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pair = AudioTextPair(root / "sample.wav", root / "sample.txt", "안녕하세요")
            output = root / "manifest.jsonl"

            write_manifest({"train": [pair], "validation": [], "test": []}, output)

            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["split"], "train")
            self.assertEqual(rows[0]["transcript"], "안녕하세요")

    def test_source_group_identifier_collapses_overlapping_chunks(self):
        root = Path("E:/dataset")
        d03 = AudioTextPair(root / "D03" / "D03_J13_S000001_merged__chunk_0001.wav", root / "D03" / "x.txt", "a")
        phish = AudioTextPair(root / "voice_phishing" / "PHISH_001_0002.wav", root / "voice_phishing" / "x.txt", "b")

        self.assertEqual(source_group_identifier(d03), "D03_J13_S000001_merged")
        self.assertEqual(source_group_identifier(phish), "PHISH_001")

    def test_source_group_identifier_collapses_generic_four_digit_chunks(self):
        pair = AudioTextPair(Path("E:/dataset/36553_들어보신_0001.wav"), Path("E:/dataset/x.txt"), "a")

        self.assertEqual(source_group_identifier(pair), "36553_들어보신")

    def test_grouped_split_keeps_all_chunks_from_source_together(self):
        root = Path("E:/dataset")
        pairs = []
        for source in ("D03_J13_S000001_merged", "D03_J13_S000002_merged", "PHISH_001", "PHISH_002"):
            for index in range(3):
                stem = f"{source}__chunk_{index:04d}"
                if source.startswith("PHISH"):
                    stem = f"{source}_{index:04d}"
                pairs.append(AudioTextPair(root / f"{stem}.wav", root / f"{stem}.txt", stem))

        splits = split_pairs_by_source(pairs, SplitRatios(0.5, 0.25, 0.25), seed=42)

        assignments = {}
        for split, items in splits.items():
            for item in items:
                assignments.setdefault(source_group_identifier(item), set()).add(split)
        self.assertTrue(all(len(split_names) == 1 for split_names in assignments.values()))


if __name__ == "__main__":
    unittest.main()

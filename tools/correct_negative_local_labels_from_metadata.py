"""Correct local negative chunk labels from the original metadata transcript."""

import argparse
import difflib
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path


ALT_PAREN_RE = re.compile(r"\(([^()]*)\)\s*/\s*\(([^()]*)\)")
ALT_RE = re.compile(r"(?P<left>[A-Za-z0-9가-힣]+)\s*/\s*(?P<right>[A-Za-z0-9가-힣]+)")
PREFIX_RE = re.compile(r"(?<![A-Za-z가-힣0-9])(?:n|o)\s*/\s*", re.IGNORECASE)
TOKEN_RE = re.compile(r"[가-힣]+|[0-9]+")
CHUNK_RE = re.compile(r"^negative_(\d{6})_(\d{4})$")


def choose_alternative(left, right):
    if re.search(r"[가-힣]", right):
        return right
    if re.search(r"[가-힣]", left):
        return left
    return right


def clean_transcript(value):
    value = str(value or "")
    value = PREFIX_RE.sub("", value)
    value = ALT_PAREN_RE.sub(lambda match: choose_alternative(match.group(1), match.group(2)), value)
    for _ in range(4):
        updated = ALT_RE.sub(lambda match: choose_alternative(match.group("left"), match.group("right")), value)
        if updated == value:
            break
        value = updated
    value = value.replace("(", " ").replace(")", " ").replace("/", " ")
    value = re.sub(r"[^가-힣0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokens(value):
    return TOKEN_RE.findall(clean_transcript(value))


def locate_span(label_tokens, original_tokens, cursor):
    if not label_tokens:
        return None, 0.0
    window_start = max(0, cursor - 250)
    window_end = min(len(original_tokens), cursor + max(400, len(label_tokens) * 2))
    window = original_tokens[window_start:window_end]
    matcher = difflib.SequenceMatcher(None, label_tokens, window, autojunk=False)
    minimum_block = 1 if len(label_tokens) <= 2 else 2
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= minimum_block]
    if not blocks:
        return None, 0.0
    first = blocks[0]
    last = blocks[-1]
    start = window_start + first.b
    end = window_start + last.b + last.size
    matched = sum(block.size for block in blocks)
    ratio = matched / max(1, len(label_tokens))
    if ratio < 0.25 or end - start > max(250, len(label_tokens) * 3):
        return None, ratio
    return (start, end), ratio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--label-root", required=True, type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    metadata_path = args.source_root / "metadata.jsonl"
    if not metadata_path.is_file():
        raise FileNotFoundError(str(metadata_path))
    if not args.label_root.is_dir():
        raise FileNotFoundError(str(args.label_root))
    if not args.backup_root.exists():
        shutil.copytree(args.label_root, args.backup_root)

    source_rows = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    original_by_id = {
        "{:06d}".format(index): tokens(row.get("text", ""))
        for index, row in enumerate(source_rows, start=1)
    }
    groups = defaultdict(list)
    for label_file in args.label_root.glob("*.txt"):
        match = CHUNK_RE.match(label_file.stem)
        if match:
            groups[match.group(1)].append((int(match.group(2)), label_file))

    report = []
    content_corrections = 0
    rewritten = 0
    empty_review = 0
    alignment_review = 0

    for source_id, items in sorted(groups.items()):
        original_tokens = original_by_id.get(source_id, [])
        cursor = 0
        for chunk_index, label_file in sorted(items):
            old_text = clean_transcript(label_file.read_text(encoding="utf-8-sig"))
            old_tokens = tokens(old_text)
            if not old_tokens:
                empty_review += 1
                report.append({"label": str(label_file), "status": "empty_review"})
                continue
            span, ratio = locate_span(old_tokens, original_tokens, cursor)
            if span is None:
                cleaned = old_text
                if cleaned != label_file.read_text(encoding="utf-8-sig").strip():
                    label_file.write_text(cleaned + "\n", encoding="utf-8")
                    rewritten += 1
                alignment_review += 1
                report.append({"label": str(label_file), "status": "alignment_review", "match_ratio": ratio})
                continue
            start, end = span
            new_text = clean_transcript(" ".join(original_tokens[start:end]))
            cursor = max(cursor, end - 30)
            if new_text != old_text:
                content_corrections += 1
            label_file.write_text(new_text + "\n", encoding="utf-8")
            rewritten += 1
            report.append({"label": str(label_file), "status": "corrected", "match_ratio": ratio})

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in report), encoding="utf-8")
    print("source rows:", len(source_rows))
    print("chunk groups:", len(groups))
    print("rewritten labels:", rewritten)
    print("content corrections:", content_corrections)
    print("empty review:", empty_review)
    print("alignment review:", alignment_review)
    print("backup:", args.backup_root)
    print("report:", args.report)


if __name__ == "__main__":
    main()

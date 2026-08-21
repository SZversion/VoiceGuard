"""Create a Colab notebook that recovers only missing chunk labels."""

import json
from pathlib import Path


def lines(text):
    return text.splitlines(keepends=True)


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("""# WhisperX 누락 라벨 복구

기존 라벨 파일은 건드리지 않고, manifest에는 있지만 라벨이 없는 청크만 복구합니다.
깨진 `source_audio` 파일명은 통화 ID와 카테고리로 원본을 찾습니다.
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# Colab 의존성
%pip install -q -U whisperx==3.7.4 jiwer soundfile
%pip uninstall -y -q torchvision
print('WhisperX dependencies ready')
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import json
import re
import difflib
from collections import defaultdict

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
SOURCE_ROOT = DRIVE_ROOT / 'data'
CHUNK_ROOT = DRIVE_ROOT / 'data_chunked_30s_overlap10_v2'
LABEL_ROOT = DRIVE_ROOT / '30s_overlap10_label_v3_complete'
MANIFEST_PATH = CHUNK_ROOT / 'manifest.jsonl'
REPORT_PATH = LABEL_ROOT / 'recovery_report.jsonl'
REVIEW_PATH = LABEL_ROOT / 'recovery_review.jsonl'

assert SOURCE_ROOT.is_dir(), SOURCE_ROOT
assert CHUNK_ROOT.is_dir(), CHUNK_ROOT
assert LABEL_ROOT.is_dir(), LABEL_ROOT
assert MANIFEST_PATH.is_file(), MANIFEST_PATH

print('source:', SOURCE_ROOT)
print('chunks:', CHUNK_ROOT)
print('labels:', LABEL_ROOT)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""import whisperx
import torch

# PyTorch 2.6의 기본 weights_only=True 때문에 WhisperX PyAnnote 체크포인트가
# 실패하지 않도록, 신뢰된 WhisperX 체크포인트에 한해 전체 로딩을 사용합니다.
original_torch_load = torch.load
def torch_load_compat(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)
torch.load = torch_load_compat

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
COMPUTE_TYPE = 'float16' if DEVICE == 'cuda' else 'int8'
MODEL_SIZE = 'small'
print('device:', DEVICE, 'compute_type:', COMPUTE_TYPE)

audio_model = whisperx.load_model(MODEL_SIZE, DEVICE, compute_type=COMPUTE_TYPE, language='ko')
align_model, align_metadata = whisperx.load_align_model(language_code='ko', device=DEVICE)
print('WhisperX models loaded')
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""TOKEN_RE = re.compile(r'[가-힣]+|[0-9]+')
SPEAKER_RE = re.compile(r'(?<![가-힣])(?:사기범|피해자)(?![가-힣])')
MASK_RE = re.compile(r'(?<![가-힣])(?:\\(?\\s*삐\\s*[-‐‑‒–—]?\\s*\\)?)(?![가-힣])')
ID_RE = re.compile(r'(?<![0-9])([0-9]{4,})(?:_|$)')

def clean_text(text):
    text = MASK_RE.sub(' ', text)
    text = SPEAKER_RE.sub(' ', text)
    text = re.sub(r'[^가-힣0-9\\s]', ' ', text)
    return re.sub(r'\\s+', ' ', text).strip()

def tokens(text):
    return TOKEN_RE.findall(clean_text(text))

def token_list_from_words(words):
    result = []
    for word in words:
        value = clean_text(str(word.get('word', '')))
        if value:
            result.extend(TOKEN_RE.findall(value))
    return result

def map_original_tokens(original, aligned_words):
    original_tokens = tokens(original)
    observed_tokens = token_list_from_words(aligned_words)
    if not original_tokens or not observed_tokens:
        return [], 0.0
    matcher = difflib.SequenceMatcher(None, observed_tokens, original_tokens, autojunk=False)
    mapped = []
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            observed_index = block.a + offset
            original_index = block.b + offset
            if observed_index < len(aligned_words) and original_index < len(original_tokens):
                mapped.append((original_index, aligned_words[observed_index]))
    return mapped, matcher.ratio()

def normalize_path(value):
    return str(value).replace('\\\\', '/')

def row_target(row):
    relative = Path(normalize_path(row['audio'])).relative_to('data_chunked_30s_overlap10_v2')
    return LABEL_ROOT / relative.with_suffix('.txt')

def source_id(value):
    match = ID_RE.search(Path(normalize_path(value)).name)
    return match.group(1) if match else None

def source_category(value, row):
    text = normalize_path(value)
    for category in ('impersonation', 'loanScam'):
        if '/' + category + '/' in text:
            return category
    row_text = normalize_path(row.get('audio', ''))
    for category in ('impersonation', 'loanScam'):
        if '/' + category + '/' in row_text:
            return category
    return None

def layout_signature(value):
    result = []
    for char in str(value):
        if char.isspace():
            result.append(' ')
        elif char in '_()[]-.,':
            result.append(char)
        else:
            result.append('x')
    return ''.join(result)

def choose_source(raw_source, rows):
    identifier = source_id(raw_source)
    category = source_category(raw_source, rows[0])
    if identifier is None or category is None:
        return None, {'reason': 'cannot_extract_id_or_category', 'source_audio': raw_source}
    candidates = sorted((SOURCE_ROOT / category).glob(identifier + '_*.mp3'))
    if not candidates:
        candidates = sorted((SOURCE_ROOT / category).glob(identifier + '_*.wav'))
    if not candidates:
        return None, {'reason': 'source_not_found', 'source_audio': raw_source, 'id': identifier, 'category': category}
    raw_name = Path(normalize_path(raw_source)).name
    raw_signature = layout_signature(raw_name)
    scored = []
    for candidate in candidates:
        candidate_signature = layout_signature(candidate.name)
        score = difflib.SequenceMatcher(None, raw_signature, candidate_signature, autojunk=False).ratio()
        scored.append((score, candidate))
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    selected = scored[0][1]
    info = {
        'source_audio': raw_source,
        'id': identifier,
        'category': category,
        'selected_source': str(selected),
        'candidate_count': len(candidates),
        'candidate_score': scored[0][0],
        'candidates': [str(item[1]) for item in scored],
    }
    return selected, info
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""rows = [json.loads(line) for line in MANIFEST_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
missing = []
for row in rows:
    target = row_target(row)
    if not target.exists():
        missing.append(row)

groups = defaultdict(list)
for row in missing:
    groups[row['source_audio']].append(row)

print('manifest rows:', len(rows))
print('existing labels:', len(rows) - len(missing))
print('missing labels:', len(missing))
print('missing source groups:', len(groups))
if not missing:
    raise RuntimeError('누락된 라벨이 없습니다. 기존 라벨을 덮어쓰지 않고 종료합니다.')
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""reports = []
reviews = []
processed = 0

for source_index, (raw_source, source_rows) in enumerate(sorted(groups.items()), start=1):
    source_audio, match_info = choose_source(raw_source, source_rows)
    if source_audio is None:
        for row in source_rows:
            reviews.append(dict(match_info, audio=row.get('audio'), reason=match_info.get('reason', 'source_match_failed')))
        print('source match failed:', raw_source, flush=True)
        continue
    try:
        original_path = source_audio.with_suffix('.txt')
        if not original_path.is_file():
            raise FileNotFoundError(str(original_path))
        original = clean_text(original_path.read_text(encoding='utf-8-sig'))
        if not original:
            raise ValueError('original transcript is empty')
        audio = whisperx.load_audio(str(source_audio))
        result = audio_model.transcribe(audio, batch_size=8, language='ko')
        aligned = whisperx.align(result['segments'], align_model, align_metadata, audio, DEVICE, return_char_alignments=False)
        words = aligned.get('word_segments', [])
        mapped, match_ratio = map_original_tokens(original, words)
        original_tokens = tokens(original)
        for row in source_rows:
            target = row_target(row)
            if target.exists():
                continue
            start = float(row['start_seconds'])
            end = float(row['end_seconds'])
            selected = []
            for original_index, word in mapped:
                word_start = word.get('start')
                word_end = word.get('end')
                if word_start is None or word_end is None:
                    continue
                if float(word_end) > start and float(word_start) < end:
                    selected.append(original_index)
            target.parent.mkdir(parents=True, exist_ok=True)
            if selected:
                label = clean_text(' '.join(original_tokens[min(selected):max(selected) + 1]))
                target.write_text(label + '\\n', encoding='utf-8')
                status = 'created'
            else:
                target.write_text('\\n', encoding='utf-8')
                reviews.append(dict(match_info, audio=row.get('audio'), reason='no_aligned_words', match_ratio=match_ratio))
                status = 'empty_review'
            reports.append(dict(match_info, audio=row.get('audio'), status=status, match_ratio=match_ratio))
        processed += 1
        print('processed source groups:', processed, '/', len(groups), flush=True)
    except Exception as error:
        for row in source_rows:
            reviews.append(dict(match_info, audio=row.get('audio'), reason='alignment_error', error=str(error)))
        print('alignment failed:', raw_source, str(error), flush=True)

REPORT_PATH.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reports), encoding='utf-8')
REVIEW_PATH.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reviews), encoding='utf-8')
print('new labels:', len(reports))
print('review items:', len(reviews))
print('report:', REPORT_PATH)
print('review:', REVIEW_PATH)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# 복구 후 전체 검증
remaining = []
bad = []
empty = []
for row in rows:
    target = row_target(row)
    if not target.exists():
        remaining.append(str(target))
        continue
    text = target.read_text(encoding='utf-8-sig')
    if not text.strip():
        empty.append(str(target))
    if re.search(r'[^가-힣0-9\\s]', text):
        bad.append(str(target))

print('manifest rows:', len(rows))
print('label files after recovery:', len(rows) - len(remaining))
print('remaining missing:', len(remaining))
print('empty labels:', len(empty))
print('bad character files:', len(bad))
if remaining:
    print('remaining examples:', remaining[:10])
if bad:
    print('bad character examples:', bad[:10])
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'whisperx_recover_missing_labels_colab.ipynb'
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

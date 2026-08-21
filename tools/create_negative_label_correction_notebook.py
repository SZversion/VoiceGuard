"""Create a Colab notebook that corrects negative chunk labels from source text."""

import json
from pathlib import Path


def lines(text):
    return text.splitlines(keepends=True)


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("""# Negative 청크 라벨 원문 기준 보정

원본 `metadata.jsonl`의 전체 텍스트와 청크 라벨을 비교합니다.
청크 음성은 수정하지 않고, 자동 매칭 가능한 라벨만 원문 표현으로 다시 저장합니다.
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import json
import re
import difflib
import shutil
from collections import defaultdict

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
SOURCE_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset'
LABEL_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s'
BACKUP_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s_before_original_correction'
SOURCE_METADATA = SOURCE_ROOT / 'metadata.jsonl'
REPORT_PATH = LABEL_ROOT / 'original_correction_report.jsonl'

assert SOURCE_METADATA.is_file(), SOURCE_METADATA
assert LABEL_ROOT.is_dir(), LABEL_ROOT
print('source:', SOURCE_ROOT)
print('labels:', LABEL_ROOT)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""ALT_RE = re.compile(r'\\(([^()]*)\\)\\s*/\\s*\\(([^()]*)\\)')
PREFIX_RE = re.compile(r'(?<![A-Za-z가-힣0-9])(?:n|o)\\s*/\\s*', re.IGNORECASE)
TOKEN_RE = re.compile(r'[가-힣]+|[0-9]+')
CHUNK_RE = re.compile(r'^negative_(\\d{6})_(\\d{4})$')

def clean_transcript(value):
    value = str(value or '')
    value = ALT_RE.sub(lambda match: match.group(2), value)
    value = PREFIX_RE.sub('', value)
    value = value.replace('(', ' ').replace(')', ' ').replace('/', ' ')
    value = re.sub(r'[^가-힣0-9\\s]', ' ', value)
    return re.sub(r'\\s+', ' ', value).strip()

def tokens(value):
    return TOKEN_RE.findall(clean_transcript(value))

def locate_span(label_tokens, original_tokens, cursor):
    if not label_tokens:
        return None, 0.0
    start_window = max(0, cursor - 250)
    end_window = min(len(original_tokens), cursor + max(400, len(label_tokens) * 2))
    window = original_tokens[start_window:end_window]
    matcher = difflib.SequenceMatcher(None, label_tokens, window, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= 2]
    if not blocks:
        return None, 0.0
    first = blocks[0]
    last = blocks[-1]
    start = start_window + first.b
    end = start_window + last.b + last.size
    matched = sum(block.size for block in blocks)
    ratio = matched / max(1, len(label_tokens))
    if ratio < 0.25 or end - start > max(250, len(label_tokens) * 3):
        return None, ratio
    return (start, end), ratio
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""if not BACKUP_ROOT.exists():
    shutil.copytree(LABEL_ROOT, BACKUP_ROOT)
    print('backup created:', BACKUP_ROOT)
else:
    print('backup already exists:', BACKUP_ROOT)

source_rows = [json.loads(line) for line in SOURCE_METADATA.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
source_text = {}
for index, row in enumerate(source_rows, start=1):
    source_text['{:06d}'.format(index)] = clean_transcript(row.get('text', ''))

groups = defaultdict(list)
for label_file in (LABEL_ROOT / 'text').glob('*.txt'):
    match = CHUNK_RE.match(label_file.stem)
    if match:
        groups[match.group(1)].append((int(match.group(2)), label_file))

reports = []
changed = 0
rewritten = 0
unchanged = 0
empty_review = 0
alignment_review = 0

for source_index, items in sorted(groups.items()):
    original = source_text.get(source_index, '')
    original_tokens = tokens(original)
    cursor = 0
    if not original_tokens:
        for _, label_file in items:
            alignment_review += 1
            reports.append({'label': str(label_file), 'status': 'source_text_missing'})
        continue
    for chunk_index, label_file in sorted(items):
        old_text = clean_transcript(label_file.read_text(encoding='utf-8-sig'))
        old_tokens = tokens(old_text)
        if not old_tokens:
            empty_review += 1
            reports.append({'label': str(label_file), 'status': 'empty_review'})
            continue
        span, ratio = locate_span(old_tokens, original_tokens, cursor)
        if span is None:
            alignment_review += 1
            reports.append({'label': str(label_file), 'status': 'alignment_review', 'match_ratio': ratio})
            continue
        start, end = span
        new_text = clean_transcript(' '.join(original_tokens[start:end]))
        cursor = max(cursor, end - 30)
        status = 'unchanged'
        if new_text != old_text:
            changed += 1
            status = 'corrected'
        label_file.write_text(new_text + '\\n', encoding='utf-8')
        rewritten += 1
        if status == 'unchanged':
            unchanged += 1
        reports.append({'label': str(label_file), 'status': status, 'match_ratio': ratio})

REPORT_PATH.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reports), encoding='utf-8')
print('source rows:', len(source_rows))
print('chunk groups:', len(groups))
print('rewritten labels:', rewritten)
print('content corrections:', changed)
print('unchanged labels rewritten:', unchanged)
print('empty review:', empty_review)
print('alignment review:', alignment_review)
print('report:', REPORT_PATH)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# 최종 검증
label_files = list((LABEL_ROOT / 'text').glob('*.txt'))
bad = []
empty = []
for path in label_files:
    value = path.read_text(encoding='utf-8-sig')
    if not value.strip():
        empty.append(str(path))
    if re.search(r'[^가-힣0-9\\s]', value):
        bad.append(str(path))
print('label files:', len(label_files))
print('empty labels:', len(empty))
print('bad character files:', len(bad))
print('backup:', BACKUP_ROOT)
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'correct_negative_chunk_labels_from_original_colab.ipynb'
    notebook = {
        'cells': cells,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python'}},
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

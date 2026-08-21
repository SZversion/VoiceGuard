"""Create a Colab notebook that builds labels for every audio chunk by alignment."""

import json
from pathlib import Path


def lines(text):
    return text.splitlines(keepends=True)


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("""# WhisperX 전체 청크 라벨 생성

원본 음성·원본 전사문·청크 manifest를 사용해 모든 청크의 라벨을 생성합니다.
정렬되지 않은 청크는 빈 라벨로 추정하지 않고 `alignment_review.jsonl`에 기록합니다.
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""# Colab 의존성
%pip install -q -U whisperx==3.7.4 jiwer soundfile
%pip uninstall -y -q torchvision
print('WhisperX dependencies ready')
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import json
import re
import difflib
import shutil
import time
import traceback

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
SOURCE_ROOT = DRIVE_ROOT / 'data'
CHUNK_ROOT = DRIVE_ROOT / 'data_chunked_30s_overlap10_v2'
MANIFEST_PATH = CHUNK_ROOT / 'manifest.jsonl'
OUTPUT_ROOT = DRIVE_ROOT / '30s_overlap10_label_v3_complete'
TEXT_ROOT = OUTPUT_ROOT
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
TEXT_ROOT.mkdir(parents=True, exist_ok=True)

assert SOURCE_ROOT.is_dir(), SOURCE_ROOT
assert MANIFEST_PATH.is_file(), MANIFEST_PATH
print('source:', SOURCE_ROOT)
print('manifest:', MANIFEST_PATH)
print('output:', OUTPUT_ROOT)
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""import whisperx
import torch

# PyTorch 2.6의 weights_only 기본값 변경과 WhisperX PyAnnote 체크포인트를 호환시킵니다.
# WhisperX와 PyAnnote에서 내려받은 신뢰된 체크포인트를 대상으로 합니다.
original_torch_load = torch.load
def torch_load_compat(*args, **kwargs):
    # lightning_fabric가 weights_only=None을 전달해도 PyTorch 2.6의
    # 기본 안전 로딩 경로로 되돌아가지 않도록 신뢰된 WhisperX 체크포인트에
    # 대해서는 항상 전체 pickle 로딩을 사용합니다.
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
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""TOKEN_RE = re.compile(r'[가-힣]+|[0-9]+')
SPEAKER_RE = re.compile(r'(?<![가-힣])(?:사기범|피해자)(?![가-힣])')
MASK_RE = re.compile(r'(?<![가-힣])(?:\\(?\\s*삐\\s*[-‐‑‒–—]?\\s*\\)?)(?![가-힣])')

def clean_text(text):
    text = MASK_RE.sub(' ', text)
    text = SPEAKER_RE.sub(' ', text)
    text = re.sub(r'[^가-힣0-9\\s]', ' ', text)
    return re.sub(r'\\s+', ' ', text).strip()

def tokens(text):
    return TOKEN_RE.findall(clean_text(text))

def resolve_source(path_value):
    raw = str(path_value).replace('\\\\', '/')
    marker = '/data/'
    if marker in raw:
        candidate = SOURCE_ROOT / raw.split(marker, 1)[1]
        if candidate.is_file():
            return candidate
    name = Path(raw).name
    matches = list(SOURCE_ROOT.rglob(name))
    if matches:
        return matches[0]
    return None

def load_rows():
    return [json.loads(line) for line in MANIFEST_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]

def load_original_text(audio_path):
    text_path = audio_path.with_suffix('.txt')
    if not text_path.is_file():
        return None
    return clean_text(text_path.read_text(encoding='utf-8-sig'))

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
    matched = 0
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            observed_index = block.a + offset
            original_index = block.b + offset
            if observed_index < len(aligned_words) and original_index < len(original_tokens):
                mapped.append((original_index, aligned_words[observed_index]))
                matched += 1
    return mapped, matched / max(1, len(observed_tokens))
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""rows = load_rows()
groups = {}
for row in rows:
    source = resolve_source(row.get('source_audio', ''))
    if source is not None:
        groups.setdefault(str(source), []).append(row)
print('manifest rows:', len(rows))
print('source groups:', len(groups))
print('unresolved sources:', len(rows) - sum(len(value) for value in groups.values()))
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""review_path = OUTPUT_ROOT / 'alignment_review.jsonl'
report_path = OUTPUT_ROOT / 'alignment_report.jsonl'
reviews = []
reports = []
processed = 0

for source_index, (source_key, source_rows) in enumerate(sorted(groups.items()), start=1):
    source_audio = Path(source_key)
    original = load_original_text(source_audio)
    if not original:
        for row in source_rows:
            reviews.append({'audio': row.get('audio'), 'source_audio': source_key, 'reason': 'missing_original_text'})
        continue
    try:
        audio = whisperx.load_audio(str(source_audio))
        result = audio_model.transcribe(audio, batch_size=8, language='ko')
        aligned = whisperx.align(result['segments'], align_model, align_metadata, audio, DEVICE, return_char_alignments=False)
        words = aligned.get('word_segments', [])
        mapped, match_ratio = map_original_tokens(original, words)
        for row in source_rows:
            relative = Path(str(row['audio']).replace('\\\\', '/')).relative_to('data_chunked_30s_overlap10_v2')
            target = TEXT_ROOT / relative.with_suffix('.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
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
            if selected:
                original_tokens = tokens(original)
                label = clean_text(' '.join(original_tokens[min(selected):max(selected) + 1]))
                target.write_text(label + '\\n', encoding='utf-8')
                status = 'created'
            else:
                target.write_text('\\n', encoding='utf-8')
                reviews.append({'audio': row.get('audio'), 'source_audio': source_key, 'reason': 'no_aligned_words', 'match_ratio': match_ratio})
                status = 'empty_review'
            reports.append({'audio': row.get('audio'), 'source_audio': source_key, 'status': status, 'match_ratio': match_ratio})
        processed += 1
        if processed % 5 == 0:
            print('processed source groups:', processed, '/', len(groups), flush=True)
    except Exception as error:
        reviews.append({'source_audio': source_key, 'reason': 'alignment_error', 'error': str(error)})
        print('alignment failed:', source_key, str(error), flush=True)

review_path.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reviews), encoding='utf-8')
report_path.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reports), encoding='utf-8')
print('reports:', len(reports))
print('review items:', len(reviews))
print('output:', OUTPUT_ROOT)
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""# 최종 검증
label_files = list(TEXT_ROOT.rglob('*.txt'))
bad = []
empty = []
for path in label_files:
    text = path.read_text(encoding='utf-8-sig')
    if not text.strip():
        empty.append(str(path))
    if re.search(r'[^가-힣0-9\\s]', text):
        bad.append(str(path))
print('label files:', len(label_files))
print('empty labels:', len(empty))
print('bad character files:', len(bad))
print('review report:', review_path)
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'whisperx_build_all_chunk_labels_colab.ipynb'
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

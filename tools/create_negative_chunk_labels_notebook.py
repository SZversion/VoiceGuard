"""Create a Colab notebook for cleaning and chunking negative STT data."""

import json
from pathlib import Path


def lines(text):
    return text.splitlines(keepends=True)


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("""# Negative 데이터 30초 청킹 및 라벨 생성

원본 데이터는 수정하지 않고, 정리된 텍스트를 WhisperX forced alignment로 음성 시간에 맞춰
30초·10% 오버랩 청크와 라벨을 생성합니다.
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# Colab 의존성
%pip install -q -U whisperx==3.7.4 soundfile jiwer
%pip uninstall -y -q torchvision
print('dependencies ready')
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import json
import re
import math
import traceback
import numpy as np
import soundfile as sf
import whisperx
import torch

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
INPUT_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset'
OUTPUT_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s'
METADATA_PATH = INPUT_ROOT / 'metadata.jsonl'
OUTPUT_METADATA = OUTPUT_ROOT / 'metadata.jsonl'
REPORT_PATH = OUTPUT_ROOT / 'chunking_report.jsonl'
REVIEW_PATH = OUTPUT_ROOT / 'chunking_review.jsonl'

CHUNK_SECONDS = 30.0
OVERLAP_RATIO = 0.10
HOP_SECONDS = CHUNK_SECONDS * (1.0 - OVERLAP_RATIO)
SAMPLE_RATE = 16000

assert INPUT_ROOT.is_dir(), INPUT_ROOT
assert METADATA_PATH.is_file(), METADATA_PATH
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
(OUTPUT_ROOT / 'audio').mkdir(parents=True, exist_ok=True)
(OUTPUT_ROOT / 'text').mkdir(parents=True, exist_ok=True)
print('input:', INPUT_ROOT)
print('output:', OUTPUT_ROOT)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# PyTorch 2.6의 WhisperX PyAnnote 체크포인트 로딩 호환성
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
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""ALT_RE = re.compile(r'\\(([^()]*)\\)\\s*/\\s*\\(([^()]*)\\)')
PREFIX_RE = re.compile(r'(?<![A-Za-z가-힣0-9])(?:n|o)\\s*/\\s*', re.IGNORECASE)
TOKEN_RE = re.compile(r'[가-힣]+|[0-9]+')

def clean_transcript(value):
    value = str(value or '')
    value = ALT_RE.sub(lambda match: match.group(2), value)
    value = PREFIX_RE.sub('', value)
    value = value.replace('(', ' ').replace(')', ' ').replace('/', ' ')
    value = re.sub(r'[^가-힣0-9\\s]', ' ', value)
    return re.sub(r'\\s+', ' ', value).strip()

def audio_path(row):
    raw = str(row.get('file_name', '')).replace('\\\\', '/')
    candidate = INPUT_ROOT / raw
    if candidate.is_file():
        return candidate
    candidate = INPUT_ROOT / Path(raw).name
    if candidate.is_file():
        return candidate
    matches = list(INPUT_ROOT.rglob(Path(raw).name))
    return matches[0] if matches else None

def chunk_paths(index, chunk_index):
    stem = 'negative_{:06d}_{:04d}'.format(index, chunk_index)
    return OUTPUT_ROOT / 'audio' / (stem + '.wav'), OUTPUT_ROOT / 'text' / (stem + '.txt')

def write_chunk(audio, start, end, audio_target, text_target, label):
    start_index = int(round(start * SAMPLE_RATE))
    end_index = min(len(audio), int(round(end * SAMPLE_RATE)))
    part = audio[start_index:end_index]
    sf.write(str(audio_target), part, SAMPLE_RATE, subtype='PCM_16')
    text_target.write_text(label + '\\n', encoding='utf-8')
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""rows = [json.loads(line) for line in METADATA_PATH.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
reports = []
reviews = []
metadata_rows = []

for index, row in enumerate(rows, start=1):
    source_audio = audio_path(row)
    cleaned = clean_transcript(row.get('text', ''))
    if source_audio is None:
        reviews.append({'index': index, 'reason': 'audio_not_found', 'file_name': row.get('file_name')})
        continue
    if not cleaned:
        reviews.append({'index': index, 'reason': 'empty_cleaned_text', 'file_name': row.get('file_name')})
        continue
    try:
        audio = whisperx.load_audio(str(source_audio))
        duration = len(audio) / float(SAMPLE_RATE)
        segment = {'start': 0.0, 'end': duration, 'text': cleaned}
        aligned = whisperx.align([segment], align_model, align_metadata, audio, DEVICE, return_char_alignments=False)
        words = aligned.get('word_segments', [])
        if not words:
            reviews.append({'index': index, 'reason': 'no_aligned_words', 'file_name': row.get('file_name')})
            continue
        chunk_count = max(1, int(math.ceil(max(0.0, duration - CHUNK_SECONDS) / HOP_SECONDS)) + 1)
        generated = 0
        for chunk_index in range(chunk_count):
            start = chunk_index * HOP_SECONDS
            if start >= duration:
                break
            end = min(duration, start + CHUNK_SECONDS)
            selected = []
            for word in words:
                word_start = word.get('start')
                word_end = word.get('end')
                if word_start is None or word_end is None:
                    continue
                if float(word_end) > start and float(word_start) < end:
                    selected.append(word.get('word', ''))
            label = clean_transcript(' '.join(selected))
            audio_target, text_target = chunk_paths(index, chunk_index + 1)
            if audio_target.exists() and text_target.exists():
                generated += 1
                metadata_rows.append({'file_name': 'audio/' + audio_target.name, 'text': label, 'label': 'negative'})
                continue
            write_chunk(audio, start, end, audio_target, text_target, label)
            generated += 1
            metadata_rows.append({'file_name': 'audio/' + audio_target.name, 'text': label, 'label': 'negative'})
        reports.append({'index': index, 'source': str(source_audio), 'duration': duration, 'chunks': generated, 'status': 'created'})
        if index % 10 == 0:
            print('processed:', index, '/', len(rows), flush=True)
    except Exception as error:
        reviews.append({'index': index, 'file_name': row.get('file_name'), 'reason': 'processing_error', 'error': str(error), 'traceback': traceback.format_exc()})
        print('failed:', index, str(error), flush=True)

OUTPUT_METADATA.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in metadata_rows), encoding='utf-8')
REPORT_PATH.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reports), encoding='utf-8')
REVIEW_PATH.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\\n' for item in reviews), encoding='utf-8')
print('input rows:', len(rows))
print('processed rows:', len(reports))
print('chunk rows:', len(metadata_rows))
print('review rows:', len(reviews))
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""# 최종 검증
audio_files = list((OUTPUT_ROOT / 'audio').glob('*.wav'))
text_files = list((OUTPUT_ROOT / 'text').glob('*.txt'))
bad = []
for path in text_files:
    value = path.read_text(encoding='utf-8-sig')
    if re.search(r'[^가-힣0-9\\s]', value):
        bad.append(str(path))
print('audio files:', len(audio_files))
print('text files:', len(text_files))
print('metadata rows:', len(metadata_rows))
print('bad character files:', len(bad))
print('review:', REVIEW_PATH)
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'whisperx_negative_chunk_labels_colab.ipynb'
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

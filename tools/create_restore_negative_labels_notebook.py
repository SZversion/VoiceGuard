"""Create a Colab notebook that restores negative labels from the backup folder."""

import json
from pathlib import Path


def lines(text):
    return text.splitlines(keepends=True)


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("""# Negative 청크 라벨 백업 복원

`run002_negative_hf_dataset_chunked_30s_before_original_correction/text`를
`run002_negative_hf_dataset_chunked_30s/text`로 복원합니다.
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import hashlib
import shutil

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
BACKUP_TEXT_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s_before_original_correction' / 'text'
TARGET_TEXT_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s' / 'text'
AUDIO_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s' / 'audio'

assert BACKUP_TEXT_ROOT.is_dir(), BACKUP_TEXT_ROOT
assert AUDIO_ROOT.is_dir(), AUDIO_ROOT
if TARGET_TEXT_ROOT.exists():
    raise FileExistsError('target text 폴더가 이미 존재합니다. 삭제하지 않고 중단합니다: {}'.format(TARGET_TEXT_ROOT))

print('backup:', BACKUP_TEXT_ROOT)
print('target:', TARGET_TEXT_ROOT)
""")},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines("""def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

source_files = sorted(BACKUP_TEXT_ROOT.rglob('*.txt'))
TARGET_TEXT_ROOT.mkdir(parents=True, exist_ok=False)
for source in source_files:
    relative = source.relative_to(BACKUP_TEXT_ROOT)
    target = TARGET_TEXT_ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

target_files = sorted(TARGET_TEXT_ROOT.rglob('*.txt'))
source_map = {path.relative_to(BACKUP_TEXT_ROOT).as_posix(): path for path in source_files}
target_map = {path.relative_to(TARGET_TEXT_ROOT).as_posix(): path for path in target_files}
missing = sorted(set(source_map) - set(target_map))
extra = sorted(set(target_map) - set(source_map))
different = [name for name in sorted(set(source_map) & set(target_map)) if digest(source_map[name]) != digest(target_map[name])]

audio_stems = {path.stem for path in AUDIO_ROOT.glob('*.wav')}
label_stems = {path.stem for path in target_files}
audio_without_label = sorted(audio_stems - label_stems)
label_without_audio = sorted(label_stems - audio_stems)

print('backup labels:', len(source_files))
print('restored labels:', len(target_files))
print('missing after copy:', len(missing))
print('extra after copy:', len(extra))
print('different contents:', len(different))
print('audio without label:', len(audio_without_label))
print('label without audio:', len(label_without_audio))
if missing or extra or different:
    raise RuntimeError('복원 검증에 실패했습니다.')
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'restore_negative_chunk_labels_from_backup_colab.ipynb'
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

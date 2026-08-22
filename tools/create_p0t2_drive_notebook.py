"""Create the Colab notebook for P0/T2 training with a separate Drive label root."""

import json
from pathlib import Path


def lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def main() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": lines("# Whisper LoRA P0/T2 재학습\n\nDrive의 음성·라벨 폴더를 직접 매칭해 실행합니다. 음성은 복사하지 않습니다.\n")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""# Colab 런타임 의존성
%pip install -q -U accelerate peft transformers librosa soundfile pyyaml jiwer av numpy 'torchao>=0.16.0'
print('dependencies ready')
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import subprocess
import sys
import shutil

REPO_URL = 'https://github.com/aihuman-7th/proj1-e.git'
REPO_REF = 'codex/whisper-lora-p0t2-drive-v3'
drive_code_roots = [Path('/content/drive/MyDrive'), Path('/content/drive'), Path('/content/drive/MyDrive/his_voice')]
PROJECT_ROOT = next((root for root in drive_code_roots if (root / 'tools' / 'train_whisper_lora.py').exists()), None)
if PROJECT_ROOT is None:
    PROJECT_ROOT = Path('/content/proj1-e')
    if (PROJECT_ROOT / '.git').exists():
        subprocess.run(['git', 'fetch', 'origin', REPO_REF], cwd=PROJECT_ROOT, check=True)
        subprocess.run(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=PROJECT_ROOT, check=True)
    else:
        if PROJECT_ROOT.exists():
            shutil.rmtree(PROJECT_ROOT)
        clone = subprocess.run(['git', 'clone', '--depth', '1', '--branch', REPO_REF, REPO_URL, str(PROJECT_ROOT)], text=True, capture_output=True)
        if clone.returncode != 0:
            message = 'Drive/tools clone 실패. Drive/tools에 최신 코드를 업로드하세요. {}'.format(clone.stderr)
            raise RuntimeError(message)
sys.path.insert(0, str(PROJECT_ROOT))
print('code root:', PROJECT_ROOT)

DRIVE_ROOT = Path('/content/drive/MyDrive/his_voice')
AUDIO_ROOT_CANDIDATES = [
    DRIVE_ROOT / 'data_chunked_overlap10_v2',
    DRIVE_ROOT / 'data_chunked_30s_overlap10_v2',
]
POSITIVE_AUDIO_ROOT = next((path for path in AUDIO_ROOT_CANDIDATES if path.is_dir()), None)
POSITIVE_LABEL_ROOT = DRIVE_ROOT / '30s_overlap10_label_v3_complete'
NEGATIVE_ROOT = DRIVE_ROOT / 'run002_negative_hf_dataset_chunked_30s'
NEGATIVE_AUDIO_ROOT = NEGATIVE_ROOT / 'audio'
NEGATIVE_LABEL_ROOT = NEGATIVE_ROOT / 'text'
OUTPUT_ROOT = DRIVE_ROOT / 'models/whisper-lora/p0t2-drive-v3-full-positive-negative'

assert POSITIVE_AUDIO_ROOT is not None, AUDIO_ROOT_CANDIDATES
assert POSITIVE_LABEL_ROOT.is_dir(), POSITIVE_LABEL_ROOT
assert NEGATIVE_AUDIO_ROOT.is_dir(), NEGATIVE_AUDIO_ROOT
assert NEGATIVE_LABEL_ROOT.is_dir(), NEGATIVE_LABEL_ROOT
print('positive audio:', POSITIVE_AUDIO_ROOT)
print('positive labels:', POSITIVE_LABEL_ROOT)
print('negative audio:', NEGATIVE_AUDIO_ROOT)
print('negative labels:', NEGATIVE_LABEL_ROOT)
print('output:', OUTPUT_ROOT)
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""from tools.train_whisper_lora import _prepare_manifest
import inspect
import os
from collections import Counter

# configs 폴더 없이 실행할 수 있도록 P0/T2 설정을 셀에서 직접 정의합니다.
config = {
    'model_name': 'openai/whisper-small',
    'language': 'ko',
    'task': 'transcribe',
    'freeze_encoder': False,
    'data': {
        'extensions': ['.wav', '.mp3', '.flac', '.m4a', '.ogg'],
        'train_ratio': 0.8,
        'validation_ratio': 0.1,
        'test_ratio': 0.1,
        'seed': 42,
        'group_by_source': True,
    },
    'lora': {'r': 8, 'alpha': 16, 'dropout': 0.05, 'target_modules': ['q_proj', 'v_proj']},
    'training': {
        'per_device_train_batch_size': 1,
        'per_device_eval_batch_size': 1,
        'gradient_accumulation_steps': 8,
        'learning_rate': 5e-5,
        'num_train_epochs': 1,
        'max_steps': 1500,
        'save_steps': 250,
        'eval_steps': 25,
        'evaluation_strategy': 'steps',
        'save_strategy': 'steps',
        'save_total_limit': None,
        'fp16': True,
        'logging_steps': 25,
    },
}

TRAIN_DATA_ROOT = Path('/content/p0t2_positive_negative_pairs')
if TRAIN_DATA_ROOT.exists():
    import shutil
    shutil.rmtree(TRAIN_DATA_ROOT)

def link_dataset(audio_root, label_root, dataset_name):
    linked = 0
    missing_labels = 0
    for audio in audio_root.rglob('*'):
        if not audio.is_file() or audio.suffix.lower() not in config['data']['extensions']:
            continue
        rel = audio.relative_to(audio_root)
        label = label_root / rel.with_suffix('.txt')
        if not label.is_file():
            missing_labels += 1
            continue
        target_audio = TRAIN_DATA_ROOT / dataset_name / rel
        target_label = target_audio.with_suffix('.txt')
        target_audio.parent.mkdir(parents=True, exist_ok=True)
        target_label.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(audio), str(target_audio))
        os.symlink(str(label), str(target_label))
        linked += 1
    return linked, missing_labels

positive_linked, positive_missing = link_dataset(POSITIVE_AUDIO_ROOT, POSITIVE_LABEL_ROOT, 'positive')
negative_linked, negative_missing = link_dataset(NEGATIVE_AUDIO_ROOT, NEGATIVE_LABEL_ROOT, 'negative')
print('linked positive pairs:', positive_linked, 'missing labels:', positive_missing)
print('linked negative pairs:', negative_linked, 'missing labels:', negative_missing)

splits, issues = _prepare_manifest(TRAIN_DATA_ROOT, OUTPUT_ROOT, config, seed=42)
print('split counts:', {name: len(items) for name, items in splits.items()})
print('issues:', len(issues))
print('issue counts:', dict(Counter(issue.code for issue in issues)))
for issue in issues[:20]:
    print(issue.code, issue.path, issue.message)
""")},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines("""# P0/T2 LoRA 학습 실행
import argparse
import yaml
from transformers.trainer_utils import get_last_checkpoint
from transformers import Seq2SeqTrainingArguments
import tools.train_whisper_lora as train_module
from tools.train_whisper_lora import train

# Drive 구버전 train_whisper_lora.py가 max_steps를 무시하는 경우를 보정합니다.
def build_runtime_training_arguments(training, output, fp16):
    values = {
        'output_dir': str(output),
        'per_device_train_batch_size': int(training['per_device_train_batch_size']),
        'per_device_eval_batch_size': int(training['per_device_eval_batch_size']),
        'gradient_accumulation_steps': int(training['gradient_accumulation_steps']),
        'learning_rate': float(training['learning_rate']),
        'num_train_epochs': 1,
        'max_steps': 1500,
        'logging_steps': 25,
        'save_steps': 250,
        'eval_steps': 25,
        'fp16': fp16,
        'predict_with_generate': True,
        'remove_unused_columns': False,
        'report_to': [],
    }
    try:
        return Seq2SeqTrainingArguments(**values, eval_strategy='steps', save_strategy='steps')
    except TypeError:
        return Seq2SeqTrainingArguments(**values, evaluation_strategy='steps', save_strategy='steps')

train_module._build_training_arguments = build_runtime_training_arguments

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
runtime_config = OUTPUT_ROOT / '_runtime_p0t2_drive_v3.yaml'
runtime_config.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding='utf-8')
last_checkpoint = get_last_checkpoint(str(OUTPUT_ROOT))
print('resume checkpoint:', last_checkpoint or '없음, 처음부터 시작')
args = argparse.Namespace(
    data=TRAIN_DATA_ROOT,
    labels=None,
    output=OUTPUT_ROOT,
    config=runtime_config,
    model='openai/whisper-small',
    seed=42,
    resume_from_checkpoint=last_checkpoint,
    fp16=True,
    dry_run=False,
)
train(args)
""")},
    ]
    output = Path(__file__).resolve().parents[1] / 'notebooks' / 'whisper_lora_p0t2_drive_v3.ipynb'
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

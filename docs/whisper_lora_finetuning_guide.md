# Whisper LoRA 파인튜닝 가이드

이 문서는 한국어 음성 데이터를 사용해 Whisper-small 모델을 LoRA 방식으로 파인튜닝하고, CER/WER를 평가하기 위한 팀원용 안내서입니다.

## 1. 작업 개요

현재 파이프라인은 다음 구조입니다.

```text
WAV/TXT 음성 데이터
        ↓
원본 통화 기준 train/validation/test 분할
        ↓
Whisper-small + LoRA 파인튜닝
        ↓
CER/WER 평가
```

중요: 10% overlap 청크가 포함된 데이터는 청크 파일 단위가 아니라 원본 통화 단위로 분할해야 합니다. 그렇지 않으면 같은 통화의 겹치는 음성이 학습 세트와 검증 세트에 동시에 들어가 평가 수치가 부풀려질 수 있습니다.

## 2. GitHub에서 받지 않는 파일

다음 항목은 개인정보·대용량·환경 의존성 때문에 GitHub에 올리지 않습니다.

- 원본 음성 및 라벨 데이터
- 정제된 WAV/TXT 데이터 전체
- Whisper base 모델 파일
- LoRA 학습 결과물과 checkpoint
- Hugging Face cache
- `.deps`, 가상환경, 로그
- Hugging Face 토큰

정제 데이터는 별도의 공유 저장소에서 받아 프로젝트 외부 경로에 배치한 뒤 `--data` 옵션으로 연결합니다.

## 3. 환경 준비

Windows PowerShell 기준입니다. Python 실행 파일 경로는 각 PC 환경에 맞게 바꿉니다.

```powershell
$PYTHON = "E:\Program Files\whisperx-env\Scripts\python.exe"

& $PYTHON -m pip install -r requirements.txt
```

CUDA 지원 PyTorch가 설치되어 있는지 확인합니다.

```powershell
& $PYTHON -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

`torch.cuda.is_available()`가 `True`가 아니면 실제 학습을 시작하지 말고 CUDA 지원 PyTorch 환경을 먼저 준비합니다.

PEFT와 Accelerate를 Program Files에 설치할 권한이 없는 경우 프로젝트 내부 의존성 폴더를 사용할 수 있습니다.

```powershell
$DEPS = "E:\teamproject\.deps\whisper-lora"
New-Item -ItemType Directory -Force $DEPS | Out-Null
& $PYTHON -m pip install --target $DEPS --upgrade peft accelerate
```

이 경우 학습 명령은 아래처럼 실행합니다.

```powershell
& $PYTHON -c "import sys; sys.path.append(r'E:\teamproject\.deps\whisper-lora'); from tools.train_whisper_lora import main; raise SystemExit(main([ ... ]))"
```

## 4. 데이터 구조

각 WAV와 TXT는 같은 폴더에 같은 파일명으로 있어야 합니다.

```text
stt_finetuning_cleaned_v4_beep_removed/
├─ D03/
│  ├─ D03_J13_S000001_merged__chunk_0001.wav
│  └─ D03_J13_S000001_merged__chunk_0001.txt
└─ voice_phishing/
   ├─ PHISH_001_0001.wav
   └─ PHISH_001_0001.txt
```

현재 정제 데이터의 기준 구성은 다음과 같습니다.

- D03 원본 통화 100건
- 보이스피싱 원본 48건
- 총 WAV/TXT 쌍 590개
- 속도 0.9~1.1배 랜덤 변경
- RMS 정규화 후 gain 적용
- 일부 노이즈 추가
- 보이스피싱 원본 삐 소리 탐지·복원
- 20~30초 청킹
- overlap 10%

## 5. Base 모델 준비

가능하면 Hugging Face cache 대신 프로젝트에 준비한 로컬 base 모델 경로를 사용합니다.

```text
<PROJECT_ROOT>/models/base-whisper-small
```

로컬 모델을 사용할 때는 `--model`에 이 경로를 전달합니다. 모델 파일을 GitHub에 커밋하지 않습니다.

## 6. Dry-run

실제 학습 전에 데이터쌍과 분할을 확인합니다.

```powershell
$PROJECT_ROOT = "E:\teamproject"
$DATA_ROOT = "E:\shared\stt_finetuning_cleaned_v4_beep_removed"
$BASE_MODEL = "$PROJECT_ROOT\models\base-whisper-small"
$OUTPUT = "$PROJECT_ROOT\models\whisper-lora\run-local"

& $PYTHON -c "import sys; sys.path.append(r'$PROJECT_ROOT\.deps\whisper-lora'); from tools.train_whisper_lora import main; raise SystemExit(main(['--data',r'$DATA_ROOT','--output',r'$OUTPUT','--model',r'$BASE_MODEL','--config',r'$PROJECT_ROOT\configs\whisper_lora_run005.yaml','--dry-run']))"
```

정상 예시는 다음과 같습니다.

```text
counts: train=461, validation=71, test=58
issues: 0
```

`issues`가 0이 아니거나 데이터 수가 예상과 다르면 학습을 중단하고 데이터 경로와 WAV/TXT 파일명을 확인합니다.

## 7. 파인튜닝 실행

현재 권장 실험은 `run-005` 설정입니다.

- Whisper-small
- LoRA rank 8
- target modules: `q_proj`, `v_proj`
- learning rate: `5e-5`
- epoch: 2
- batch size: 2
- gradient accumulation: 8
- CUDA FP16

```powershell
& $PYTHON -c "import sys; sys.path.append(r'$PROJECT_ROOT\.deps\whisper-lora'); from tools.train_whisper_lora import main; raise SystemExit(main(['--data',r'$DATA_ROOT','--output',r'$OUTPUT','--model',r'$BASE_MODEL','--config',r'$PROJECT_ROOT\configs\whisper_lora_run005.yaml','--fp16']))"
```

학습 결과에는 다음 파일이 생성됩니다.

```text
<OUTPUT>/
├─ adapter_model.safetensors
├─ adapter_config.json
├─ tokenizer.json
├─ training_config.json
└─ checkpoint-*/
```

Base 모델은 별도로 필요하며, `adapter_model.safetensors`만으로는 완전한 Whisper 모델이 아닙니다.

## 8. CER/WER 해석

CER와 WER는 낮을수록 좋습니다.

- CER: 글자 단위 오류율
- WER: 공백으로 구분한 단어 단위 오류율

예를 들어 CER `0.50`은 평균적으로 문자 오류가 약 50% 있다는 뜻입니다. 한국어는 띄어쓰기와 숫자·기호 표기 차이의 영향을 많이 받으므로, 동일한 정규화 규칙으로 비교해야 합니다.

Validation 수치가 epoch 증가와 함께 악화되면 에폭을 무조건 늘리지 않습니다. 다음 순서로 확인합니다.

1. 원본 통화 기준 분할 여부
2. 청크 음성과 TXT 문장의 시간 정합성
3. learning rate 감소
4. epoch 감소
5. D03과 보이스피싱 데이터를 분리한 CER/WER

## 9. 자주 발생하는 오류

### `ModuleNotFoundError: No module named 'peft'`

PEFT가 학습 환경에 없는 상태입니다. `requirements.txt`를 설치하거나 위의 프로젝트 로컬 `.deps` 설치 방법을 사용합니다.

### `PermissionError` in `Program Files` 또는 `hf-cache`

Program Files와 Hugging Face cache의 쓰기 권한 문제입니다.

- 로컬 base 모델 경로를 `--model`로 지정합니다.
- PEFT/Accelerate는 프로젝트 `.deps`에 설치합니다.
- Hugging Face token을 코드나 GitHub에 저장하지 않습니다.

### `torch.cuda.is_available() == False`

CPU 전용 PyTorch가 설치된 상태입니다. CUDA 지원 PyTorch와 GPU 드라이버를 준비한 뒤 다시 확인합니다.

### `issues`가 0이 아님

대부분 다음 원인입니다.

- WAV/TXT 파일명 불일치
- TXT가 비어 있음
- 지원하지 않는 오디오 확장자
- 데이터 경로 오기입

## 10. AI 도구에 작업을 요청할 때 제공할 정보

AI 도구를 사용할 때는 다음 정보를 함께 전달하면 재현성이 높아집니다.

```text
목표: Whisper-small 한국어 모델 LoRA 파인튜닝
데이터: WAV/TXT 쌍, 원본 통화 기준 분할 필요
데이터 경로: <DATA_ROOT>
base 모델 경로: <BASE_MODEL>
출력 경로: <OUTPUT>
설정 파일: configs/whisper_lora_run005.yaml
환경: Windows, CUDA GPU, FP16
먼저 dry-run으로 데이터 수와 issues를 확인할 것
학습 후 validation 및 test CER/WER를 보고할 것
```

토큰, 비밀번호, 개인 음성 데이터, 개인 PC의 사용자 경로는 AI 도구나 GitHub에 입력하지 않습니다.

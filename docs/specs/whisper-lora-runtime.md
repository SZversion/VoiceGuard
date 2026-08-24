# Spec — Whisper LoRA runtime 연결

## Why

- **페르소나**: 한국어 통화 음성 분석 backend를 운영·검증하는 개발자
- **상황**: FastAPI analyzer에는 STT adapter 경계가 있지만 현재 구현은 Faster-Whisper 기본 모델만 사용한다.
- **문제**:
  1. 요청된 openai/whisper-small base model과 VoiceGuardproject/whisper-lora-run-011 adapter가 실제 runtime에 적용되지 않았다.
  2. LoRA adapter가 적용되지 않은 상태를 fine-tuned STT가 동작한다고 오인할 수 있다.
  3. 실제 Hugging Face 다운로드 없이 loader와 adapter 계약을 검증할 테스트 경계가 없다.
- **측정 지표**: base/adapter 로딩 성공 여부, adapter 적용 여부, 한국어 transcript 생성 여부, 분류모델과의 E2E 연결 여부, 실제 모델 추론 시간·메모리 기록

## Goal

- openai/whisper-small을 base model로 로드한다.
- VoiceGuardproject/whisper-lora-run-011를 PEFT LoRA adapter로 base model에 적용한다.
- WhisperProcessor와 결합한 Transcriber adapter를 VoicePhishingAnalyzer에 주입할 수 있다.
- 분류모델 user0074/voice-phishing-koelectra와 함께 FastAPI startup에서 로드할 수 있다.
- loader와 analyzer wiring은 fake dependency injection으로 실제 다운로드 없이 테스트할 수 있다.
- 실제 모델 검증에서는 모델 상태, transcript, classifier result, job result를 기록한다.

**성공 기준**

- loader가 지정된 base와 adapter repository에서 모델을 로드한다.
- inference는 adapter가 적용된 객체를 사용한다.
- 한국어 음성에서 비어 있지 않은 transcript를 반환한다.
- 두 모델이 모두 준비되면 model-status의 analyzable이 true가 된다.
- 실제 음성 업로드가 job 완료와 결과 조회까지 진행된다.

**Out of Scope**

- LoRA 재학습 또는 adapter 수정
- ONNX/CTranslate2 변환
- STT CER/WER 품질 개선
- 분류 threshold tuning과 새 평가 dataset 구축
- 실시간 streaming STT
- 모델 hot reload

## What

### Happy Path

1. startup이 WhisperProcessor를 base repository에서 로드한다.
2. WhisperForConditionalGeneration을 openai/whisper-small에서 로드한다.
3. PeftModel.from_pretrained로 VoiceGuardproject/whisper-lora-run-011를 적용한다.
4. model을 evaluation mode로 전환한다.
5. audio bytes를 16kHz mono waveform으로 변환한다.
6. processor가 input features를 생성한다.
7. torch.no_grad 상태에서 transcription token을 생성한다.
8. processor가 token을 한국어 transcript로 decode한다.
9. analyzer가 transcript를 classifier에 전달한다.
10. job result API가 기존 result contract를 반환한다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | base model 로딩 실패 | STTModelLoadError로 변환 |
| EC-02 | adapter repository 로딩 실패 | STTModelLoadError로 변환 |
| EC-03 | adapter가 base model과 호환되지 않음 | startup 상태를 error로 기록하고 analyzer 미생성 |
| EC-04 | audio bytes가 비어 있음 | AudioInputError |
| EC-05 | audio decode 실패 | TranscriptionError, 임시자료 삭제 |
| EC-06 | 한국어가 아닌 음성 | UnsupportedLanguageError |
| EC-07 | transcript가 비어 있음 | TranscriptionError |
| EC-08 | 실제 모델 다운로드 불가능 | fake loader 테스트와 runtime error 상태로 분리 |
| EC-09 | CPU 메모리·시간 부족 | 실제 검증 로그에 측정값 기록, production-ready 주장 금지 |

## How

### Model constants

- BASE_MODEL = 'openai/whisper-small'
- ADAPTER_MODEL = 'VoiceGuardproject/whisper-lora-run-011'
- CLASSIFIER_MODEL = 'user0074/voice-phishing-koelectra'

### Runtime dependencies

- transformers
- torch
- peft
- audio decoder dependency는 repository의 preprocessing 경계와 맞춰 결정한다.
- 실제 모델 테스트는 deterministic unit test와 분리한다.

### Loader boundary

- app/analysis/whisper_lora_loader.py: processor, base model, adapter 로딩과 오류 변환
- app/analysis/whisper_transcriber.py: audio decode, processor/model.generate, 언어·빈 transcript 검증
- loader가 반환하는 객체는 기존 Transcriber protocol을 만족한다.
- analyzer와 API contract는 변경하지 않는다.

### Test isolation

- loader factory와 model/processor/PEFT 객체를 주입한다.
- unit test는 네트워크와 실제 weight 다운로드를 수행하지 않는다.
- 실제 모델 검증은 별도 opt-in 명령으로 실행한다.
- 실제 음성 원본과 transcript는 저장소에 기록하지 않는다.

## AC

### AC-01 · base model 로딩

- **GIVEN**: fake processor와 base model factory가 정상 객체를 반환한다.
- **WHEN**: Whisper LoRA loader를 호출한다.
- **THEN**: openai/whisper-small이 base model 식별자로 전달된다.

### AC-02 · adapter 적용

- **GIVEN**: fake base model과 fake PEFT loader가 정상 동작한다.
- **WHEN**: loader가 초기화된다.
- **THEN**: VoiceGuardproject/whisper-lora-run-011가 adapter 식별자로 전달되고 inference model은 adapter 객체다.

### AC-03 · loader 실패

- **GIVEN**: base model 또는 adapter 로딩이 실패한다.
- **WHEN**: loader가 실행된다.
- **THEN**: STTModelLoadError가 발생한다.

### AC-04 · analyzer 연결

- **GIVEN**: Whisper LoRA transcriber와 KoELECTRA classifier가 준비된다.
- **WHEN**: FastAPI lifespan이 시작된다.
- **THEN**: analyzer가 생성되고 analyzable=true가 된다.

### AC-05 · 실제 STT

- **GIVEN**: 실제 음성 파일과 base/adapter model download가 가능하다.
- **WHEN**: transcriber가 음성을 처리한다.
- **THEN**: 비어 있지 않은 한국어 transcript를 반환한다.

### AC-06 · 실제 E2E

- **GIVEN**: 실제 STT와 classifier가 모두 준비된다.
- **WHEN**: 음성 파일을 API에 업로드한다.
- **THEN**: job이 완료되고 결과 API에서 label과 suspicion score를 반환한다.

### AC-07 · 개인정보 보호

- **GIVEN**: 실제 음성 파일로 검증을 수행한다.
- **WHEN**: 검증이 종료된다.
- **THEN**: 원본 음성·전사문·분석 임시자료가 저장소에 남지 않는다.
# Spec — PyTorch KoELECTRA Classifier Runtime Rollback

## Why

현재 ONNX INT8 classifier runtime에서 suspicion score가 0.99 이상으로 포화되는 현상이 관찰되었다. 원래 PyTorch classifier와 동일 입력의 logits·score를 비교해 원인을 확인하기 위해 FastAPI startup runtime을 PyTorch loader로 임시 롤백한다.

## Goal

- FastAPI startup에서 `load_text_classifier`를 사용한다.
- 기존 모델 ID `user0074/voice-phishing-koelectra`, max length 128, label mapping `0=normal`, `1=voice_phishing`을 유지한다.
- 기존 analyzer·API response contract를 변경하지 않는다.
- PyTorch classifier runtime과 ONNX runtime의 동작을 비교할 수 있는 상태를 만든다.

Out of scope:

- threshold 또는 score calibration 변경
- ONNX 파일 삭제
- 모델 재학습
- STT runtime 변경

## What

### Happy Path

1. FastAPI startup에서 Whisper STT와 PyTorch KoELECTRA classifier를 한 번씩 로드한다.
2. 두 모델이 준비되면 `analyzable=true`가 된다.
3. analyzer는 기존 `TextClassifier` 계약으로 텍스트를 분류한다.

### Edge Case

- PyTorch 또는 Transformers 의존성이 없으면 classifier 상태를 `error`로 기록한다.
- 모델 다운로드 또는 초기화 실패 시 기존 `MODEL.NOT_READY` 계약을 유지한다.
- ONNX 관련 파일과 테스트는 비교 실험을 위해 보존한다.

## How

- loader: `app.analysis.model_loader.load_text_classifier`
- model: `user0074/voice-phishing-koelectra`
- max length: `128`
- device: existing PyTorch model default behavior
- dependencies: `transformers==4.44.2`, `torch==2.4.1`
- runtime selection: FastAPI default classifier loader를 PyTorch loader로 지정

## AC

### AC1 — PyTorch loader 연결

Given FastAPI startup과 주입되지 않은 기본 classifier loader일 때
When runtime을 초기화하면
Then `load_text_classifier`가 호출되고 classifier 상태가 `ready`가 된다.

### AC2 — 기존 API 계약 유지

Given STT와 PyTorch classifier가 모두 준비될 때
When `/api/model-status`를 조회하면
Then `stt=ready`, `classifier=ready`, `analyzable=true`를 반환한다.

### AC3 — 로더 실패 처리

Given PyTorch classifier loader가 예외를 발생시킬 때
When startup이 실행되면
Then 앱은 시작되고 classifier 상태는 `error`, analyzable은 `false`가 된다.
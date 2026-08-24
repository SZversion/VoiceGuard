# Spec — KoELECTRA 분류모델 연결

## Why

- **페르소나**: 음성 통화 분석 결과를 확인하는 사용자와 Nuxt.js 프론트엔드 담당자
- **상황**: STT가 생성한 한국어 transcript를 보이스피싱 여부로 분류해야 한다.
- **문제**: 현재 백엔드에는 실제 Analyzer와 분류모델이 연결되어 있지 않아 분석 작업을 완료할 수 없다.
- **측정 지표**: 모델 로딩 성공 여부, 분류 결과 계약 준수 여부, 모델 미준비·입력 오류 처리 여부

## Goal

- Hugging Face `user0074/voice-phishing-koelectra`를 백엔드 Analyzer에서 사용할 수 있다.
- 모델 입력은 STT가 생성한 한국어 transcript이다.
- 모델 결과는 다음 매핑을 사용한다.
  - `0`: `normal`
  - `1`: `voice_phishing`
- 결과에는 `label`, `suspicion_score`, `reference_segments`, `guidance`가 포함된다.
- 모델은 앱 시작 시 한 번 로드하며 요청마다 다시 로드하지 않는다.
- 모델이 준비되지 않으면 분석 API는 `503 MODEL.NOT_READY`를 반환한다.
- 단위 테스트는 실제 Hugging Face 모델 다운로드 없이 실행할 수 있다.

### Out of Scope

- 모델 재학습 또는 데이터셋 변경
- 모델을 ONNX INT8로 변환하는 작업
- STT 모델 자체의 구현 또는 성능 개선
- 실시간 통화 분석
- 모델 성능을 새로 측정하거나 품질을 보증하는 작업

## What

### Happy Path

1. 앱 시작 시 tokenizer와 sequence classification model을 로드한다.
2. Analyzer가 STT transcript를 입력받는다.
3. transcript를 tokenizer로 변환한다.
4. 최대 128 tokens로 추론한다.
5. logits를 probability로 변환한다.
6. 예측 class id를 `normal` 또는 `voice_phishing`으로 매핑한다.
7. 기존 API 결과 계약에 맞춰 결과를 반환한다.

### Edge Cases

- 모델 로딩 실패: classifier 상태를 `error`로 기록하고 분석을 거절한다.
- 빈 transcript: 분석 가능한 입력이 아니므로 명시적인 오류를 반환한다.
- 128 tokens 초과 transcript: `truncation=True`로 제한한다.
- 모델 출력 class id가 0 또는 1이 아님: 분석 실패로 처리한다.
- 실제 모델 대신 테스트 대체 analyzer를 사용하여 API 테스트를 수행한다.

## How

### Model

- Model ID: `user0074/voice-phishing-koelectra`
- Architecture: `ElectraForSequenceClassification`
- Runtime format: PyTorch `pytorch_model.bin`
- Base model: `skplanet/dialog-koelectra-small-discriminator`
- `max_length`: `128`
- `num_labels`: `2`
- Label mapping:
  - `0`: `normal`
  - `1`: `voice_phishing`

### Runtime Design

- `Analyzer` Protocol의 `analyze(audio: bytes)` 계약을 유지한다.
- STT와 분류 책임을 구현체 내부에서 분리할 수 있도록 한다.
- tokenizer와 model은 앱 초기화 시 로드하고 `app.state`를 통해 관리한다.
- `/api/model-status`는 실제 로딩 상태를 반환한다.
- 실제 모델 의존 테스트와 API 계약 테스트를 분리한다.
- 모델 파일과 음성·전사 데이터는 저장소에 커밋하지 않는다.

### Result Contract

```json
{
  "label": "normal",
  "suspicion_score": 0.1,
  "reference_segments": [],
  "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요."
}
```

`suspicion_score`는 모델의 예측 확률이며 법적·수사적 확정 판정으로 표현하지 않는다.

## AC

### AC-01 · 모델 준비 상태

- **GIVEN**: STT와 분류모델이 정상적으로 로드됐다.
- **WHEN**: `GET /api/model-status`를 호출한다.
- **THEN**: classifier 상태가 `ready`이고 분석 가능 상태가 `true`로 반환된다.

### AC-02 · 분류 결과

- **GIVEN**: 테스트용 analyzer에 한국어 transcript가 전달된다.
- **WHEN**: analyzer가 분석을 수행한다.
- **THEN**: `label`, `suspicion_score`, `reference_segments`, `guidance`를 반환한다.

### AC-03 · label 매핑

- **GIVEN**: 모델의 예측 class id가 0 또는 1이다.
- **WHEN**: 결과를 변환한다.
- **THEN**: 0은 `normal`, 1은 `voice_phishing`으로 반환한다.

### AC-04 · 모델 미준비

- **GIVEN**: 분류모델이 로드되지 않았다.
- **WHEN**: 지원 형식의 음성 파일로 `POST /api/analyze`를 호출한다.
- **THEN**: HTTP 503과 `MODEL.NOT_READY`를 반환한다.

### AC-05 · 모델 로딩 실패

- **GIVEN**: Hugging Face 모델 로딩 중 예외가 발생한다.
- **WHEN**: 앱 초기화가 완료된다.
- **THEN**: 서버는 상태를 `error`로 기록하고 모델 미준비 상태로 분석을 거절한다.

### AC-06 · 입력 길이 제한

- **GIVEN**: transcript가 128 tokens를 초과한다.
- **WHEN**: 분류를 수행한다.
- **THEN**: 입력을 truncation하고 예외 없이 결과를 반환한다.

### AC-07 · 테스트 격리

- **GIVEN**: API 계약 테스트를 실행한다.
- **WHEN**: 테스트 대체 analyzer를 주입한다.
- **THEN**: 실제 Hugging Face 모델 다운로드 없이 테스트가 실행된다.


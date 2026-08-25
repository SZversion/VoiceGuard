> Status: 이 문서는 ONNX INT8 구현 사양을 보존한다. 현재 `SJH30/fix/pytorch-classifier-runtime` 브랜치에서는 score 비교를 위해 FastAPI 기본 runtime을 PyTorch loader로 임시 롤백한다.
# Spec — ONNX INT8 KoELECTRA 분류기

## Why

- **페르소나**: Railway에서 음성 분석 API를 운영하는 백엔드 담당자
- **상황**: 현재 PyTorch KoELECTRA 분류기를 CPU 환경에서 사용하고 있다.
- **문제**:
  1. 텍스트 청크가 많을 때 CPU 분류 추론 시간이 길어질 수 있다.
  2. Railway 메모리 사용량을 줄일 수 있는 ONNX INT8 변환본이 이미 존재하지만 API runtime에는 연결되어 있지 않다.
  3. 모델 교체 시 기존 API 계약과 analyzer 인터페이스를 유지해야 한다.
- **측정 지표**: 동일 입력에 대한 label 일치율, suspicion score 차이, warm inference latency.

## Goal

- **해결 목표**: `user0074/voice-phishing-koelectra`의 `koelectra_v1_onnx_int8/model_quantized.onnx`를 기존 분류기 계약에 연결한다.
- **성공 기준**:
  - `classify()`가 기존 `ClassifierOutput`을 반환한다.
  - 라벨 매핑 `0=normal`, `1=voice_phishing`을 유지한다.
  - 빈 텍스트 입력을 기존과 동일하게 거부한다.
  - 모델 로더 오류가 `ModelLoadError`로 변환된다.
  - FastAPI runtime이 ONNX INT8 loader만 사용한다.
- **Out of Scope**: 분류 threshold 변경, STT 변경, batch inference, API response schema 변경, Railway 기본 모델 전환 전의 성능 결론.

## What

**Happy Path**

1. ONNX tokenizer와 CPU `InferenceSession`을 startup에 한 번 생성한다.
2. `OnnxTextClassifier`가 텍스트를 max length 128로 tokenize한다.
3. ONNX logits를 softmax로 변환한다.
4. 기존 라벨과 `ClassifierOutput` 형식으로 반환한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 빈 transcript | `ValueError` 반환 |
| EC-02 | ONNX 파일 또는 tokenizer 누락 | `ModelLoadError` 반환 |
| EC-03 | 지원하지 않는 ONNX 입력 이름 | 로더/추론 오류를 `ModelLoadError` 또는 runtime 오류로 명확히 보고 |
| EC-04 | logits class 수가 2개가 아님 | `ValueError` 반환 |
| EC-05 | ONNX 초기화 실패 | `ModelLoadError`를 기록하고 runtime을 not analyzable 상태로 둔다 |

## How

- 모델 저장소: `user0074/voice-phishing-koelectra`
- 모델 subfolder: `koelectra_v1_onnx_int8`
- 모델 파일: `model_quantized.onnx`
- 실행 provider: `CPUExecutionProvider`
- tokenizer: 같은 ONNX subfolder의 tokenizer 파일
- max length: `128`
- 라벨: `0=normal`, `1=voice_phishing`
- dependency: `onnxruntime`
- 기존 `TextClassifier`의 API 계약과 `ClassifierOutput`을 변경하지 않는다.
- FastAPI runtime에서는 PyTorch loader를 사용하지 않는다.

## AC (Given-When-Then)

**AC-01 · 정상적인 ONNX 분류 출력**

- GIVEN: 유효한 ONNX session과 tokenizer
- WHEN: 한국어 transcript를 `classify()`에 전달
- THEN: `ClassifierOutput`과 0~1 범위의 suspicion score를 반환한다.

**AC-02 · 빈 텍스트 거부**

- GIVEN: 빈 transcript
- WHEN: `classify()`를 호출
- THEN: `ValueError`를 반환한다.

**AC-03 · 두 클래스 검증**

- GIVEN: 두 개가 아닌 logits를 반환하는 session
- WHEN: `classify()`를 호출
- THEN: 지원하지 않는 class id 오류를 반환한다.

**AC-04 · ONNX runtime 선택**

- GIVEN: FastAPI startup
- WHEN: runtime이 classifier를 초기화
- THEN: ONNX INT8 loader가 사용되고 `model-status`가 ready가 된다.

**AC-05 · chunking 호환**

- GIVEN: 128 token을 초과하는 transcript
- WHEN: ONNX classifier의 `classify_chunks()`를 호출
- THEN: 각 chunk에 대한 `ClassifierOutput` 목록을 반환한다.
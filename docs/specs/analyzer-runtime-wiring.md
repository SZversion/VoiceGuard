# Spec — Analyzer runtime wiring

## Why

- **페르소나**: 음성 분석 API를 운영·검증하는 백엔드 개발자와 Nuxt.js 프론트엔드 담당자
- **상황**: STT adapter와 KoELECTRA classifier는 각각 구현되었지만 FastAPI app startup에서 함께 생성되어 `VoicePhishingAnalyzer`로 연결되지 않았다.
- **문제**:
  1. 두 모델이 준비되어도 `app.state.analyzer`가 `None`이라 분석 요청이 항상 `MODEL.NOT_READY`가 된다.
  2. 한 모델만 로드된 상태를 전체 분석 가능 상태로 오인할 위험이 있다.
  3. 실제 모델 다운로드 없이 runtime wiring을 검증할 테스트 경계가 없다.
- **측정 지표**: startup 모델 상태의 정확성, analyzer 생성 조건, `POST /api/analyze`의 준비/미준비 응답 계약, 실제 모델 없는 통합 테스트 재현성

## Goal

- FastAPI lifespan에서 STT transcriber와 classifier를 각각 한 번 로드한다.
- 두 모델이 모두 `ready`일 때만 `VoicePhishingAnalyzer`를 생성해 `app.state.analyzer`에 저장한다.
- 하나라도 `not_ready` 또는 `error`이면 analyzer를 생성하지 않고 `analyzable=false`를 반환한다.
- 기존 `GET /api/model-status`, `POST /api/analyze`, analyzer result contract를 유지한다.
- loader를 주입한 테스트로 실제 모델 다운로드 없이 성공·실패 경로를 검증한다.

**성공 기준**

- STT와 classifier가 모두 성공하면 `stt=ready`, `classifier=ready`, `analyzable=true`가 된다.
- 둘 중 하나라도 실패하면 해당 상태가 `error`, analyzer가 `None`, `analyzable=false`가 된다.
- analyzer가 없는 상태의 유효한 업로드는 HTTP 503과 `MODEL.NOT_READY`를 반환한다.
- analyzer가 주입된 상태의 업로드는 기존 job 생성 계약을 따른다.
- 전체 테스트가 실제 외부 모델 다운로드 없이 통과한다.

**Out of Scope**

- STT 또는 classifier 내부 알고리즘 변경
- 모델 재학습·양자화·성능 개선
- transcript 청킹·통화 단위 집계·위험 표현 추출
- API 결과 schema의 확장
- 모델 hot reload와 runtime 관리자 API
- startup 모델 병렬 로딩 최적화

## What

### Happy Path

1. FastAPI lifespan이 시작된다.
2. STT loader가 `FasterWhisperTranscriber`를 반환한다.
3. classifier loader가 `TextClassifier`를 반환한다.
4. app이 두 객체를 `VoicePhishingAnalyzer`에 주입한다.
5. `app.state.analyzer`가 생성되고 model status가 ready/analyzable로 갱신된다.
6. 유효한 음성 업로드가 analyzer를 사용하는 job으로 생성된다.
7. job runner가 analyzer 결과를 기존 result contract로 저장한다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | STT loader 실패 | `stt=error`, `classifier` 상태는 독립적으로 기록, analyzer 미생성 |
| EC-02 | classifier loader 실패 | `classifier=error`, `stt` 상태는 독립적으로 기록, analyzer 미생성 |
| EC-03 | 두 loader 모두 실패 | 두 상태를 각각 `error`로 기록, analyzer 미생성 |
| EC-04 | lifespan 외부에서 model-status 호출 | 기존처럼 모든 모델을 `not_ready`, analyzable=false로 반환 |
| EC-05 | analyzer 미준비 상태에서 유효한 업로드 | 기존 `503 MODEL.NOT_READY` 응답 유지 |
| EC-06 | 테스트 analyzer 주입 | 실제 loader를 호출하지 않고 job 생성·결과 API 테스트 가능 |
| EC-07 | analyzer 실행 중 STT/classifier 예외 | 기존 JobRunner의 `ANALYSIS.FAILED` 처리와 임시자료 정리 유지 |

## How

### 변경 파일 경계

`@text
app/api/main.py
  ├─ create_app의 loader injection
  ├─ lifespan runtime initialization
  └─ app.state.transcriber/classifier/analyzer/model_status 관리

app/api/routes/health.py
  └─ 기존 runtime status 응답 유지

tests/api/test_model_runtime.py
  └─ startup 성공·부분 실패·analyzer 생성 조건 검증

tests/api/test_analyze_upload.py 또는 별도 runtime API test
  └─ model ready/not ready API 계약 검증
`@

### Runtime initialization

`create_app`은 다음 optional dependency injection을 제공한다.

`@python
create_app(
    stt_loader: Callable[[], Transcriber] | None = None,
    classifier_loader: Callable[[], TextClassifier] | None = None,
)
`@

- 인자가 없으면 production loader를 사용한다.
- lifespan에서 loader를 호출한다.
- 각 loader 오류는 앱 startup 자체를 중단시키지 않고 해당 model status를 `error`로 기록한다.
- 두 모델이 모두 성공한 경우에만 `VoicePhishingAnalyzer`를 생성한다.
- `analyzable`은 `app.state.analyzer is not None`과 동일한 의미를 갖는다.

### 상태 계약

`@json
{
  "stt": "ready | not_ready | error",
  "classifier": "ready | not_ready | error",
  "analyzable": true
}
`@

모델 결과와 분석 결과는 법적·수사적 확정 판정으로 표현하지 않는다. 이번 단계에서 새로운 API error code는 추가하지 않는다.

### 테스트 격리

- fake STT loader와 fake classifier loader를 주입한다.
- fake analyzer 또는 실제 `VoicePhishingAnalyzer`를 선택적으로 사용한다.
- Hugging Face와 Faster-Whisper 모델 다운로드를 수행하지 않는다.
- 기존 전역 `app` 테스트가 lifespan 상태에 의존하지 않도록 `create_app()`로 독립 app을 만든다.

## AC

### AC-01 · 양쪽 모델 준비

- **GIVEN**: STT loader와 classifier loader가 각각 정상 객체를 반환한다.
- **WHEN**: app lifespan이 시작된다.
- **THEN**: `app.state.analyzer`가 생성되고 model status가 `ready`, `ready`, `true`가 된다.

### AC-02 · STT 준비 실패

- **GIVEN**: STT loader가 예외를 발생시킨다.
- **WHEN**: app lifespan이 시작된다.
- **THEN**: `stt=error`, analyzer는 `None`, `analyzable=false`가 된다.

### AC-03 · classifier 준비 실패

- **GIVEN**: classifier loader가 예외를 발생시킨다.
- **WHEN**: app lifespan이 시작된다.
- **THEN**: `classifier=error`, analyzer는 `None`, `analyzable=false`가 된다.

### AC-04 · 모델 미준비 분석 요청

- **GIVEN**: analyzer가 생성되지 않았다.
- **WHEN**: 지원 형식의 유효한 audio로 `POST /api/analyze`를 호출한다.
- **THEN**: HTTP 503과 `MODEL.NOT_READY`를 반환한다.

### AC-05 · 모델 준비 분석 요청

- **GIVEN**: analyzer가 생성되었다.
- **WHEN**: 지원 형식의 유효한 audio로 `POST /api/analyze`를 호출한다.
- **THEN**: HTTP 202와 `job_id`, `status=queued`를 반환한다.

### AC-06 · analyzer 결과 연결

- **GIVEN**: fake transcriber와 fake classifier가 주입된 analyzer가 실행된다.
- **WHEN**: job runner가 분석을 완료한다.
- **THEN**: `label`, `suspicion_score`, `reference_segments`, `guidance` 결과 계약을 유지한다.

### AC-07 · 테스트 격리

- **GIVEN**: runtime wiring 테스트를 실행한다.
- **WHEN**: fake loader를 주입한다.
- **THEN**: 외부 모델 다운로드 없이 테스트가 통과한다.
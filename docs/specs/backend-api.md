# Backend API Spec — 음성 분석 MVP

## Why

- **페르소나**: 통화 녹음파일의 위험성을 빠르게 확인하려는 웹 사용자
- **상황**: Nuxt 프론트엔드가 음성파일을 업로드하고, FastAPI가 비동기로 STT·분류를 수행한다.
- **문제**:
  1. 모델이 준비되지 않아도 서버 상태와 모델 상태를 구분해 보여줘야 한다.
  2. 음성 분석은 시간이 걸리므로 업로드 요청과 결과 조회를 분리해야 한다.
  3. 원본 음성·전사문·중간 결과를 저장하지 않고 작업 종료 후 삭제해야 한다.
- **측정 지표**: 정상·손상·비한국어·모델 미준비 입력의 API 오류 계약 테스트 100% 통과, 성공·실패·취소 정리 경로 테스트 100% 통과

## Goal

- **해결 목표**: 모델 기반 음성 분석을 작업 단위로 실행하고 프론트엔드가 상태와 결과를 안정적으로 조회한다.
- **성공 기준**:
  - 서버가 모델 파일 없이도 시작되고 `GET /api/v1/health`가 `200`을 반환한다.
  - `GET /api/v1/model-status`가 `loading`, `ready`, `error` 중 하나를 반환한다.
  - 모델 미준비 시 `POST /api/v1/analyze`가 `503`과 `MODEL.NOT_READY`를 반환한다.
  - 테스트용 fake analyzer로 `queued → preprocessing → transcribing → classifying → finalizing → completed` 흐름을 검증한다.
  - 성공·실패·취소 시 임시파일과 중간 상태를 정리한다.
- **Out of Scope**: 회원가입·인증, DB·외부 큐, 분석 이력, 실시간 통화 분석, 실제 모델 가중치 제공, 자동 신고·차단

## What

### Happy Path

1. 서버 시작 시 환경변수와 STT·분류 모델 경로를 확인한다.
2. 프론트엔드가 health와 model-status를 조회한다.
3. 모델이 `ready`이면 사용자가 `.wav`, `.mp3`, `.m4a` 파일을 업로드한다.
4. 서버가 확장자, 파일 시그니처, 음성 스트림과 손상 여부를 확인하고 IP rate limit·중복 작업 잠금을 검사한다.
5. 서버가 임시파일과 `job_id`를 만들고 `202`로 반환한다.
6. 작업은 `preprocessing`, `transcribing`, `classifying`, `finalizing` 단계를 거친다.
7. 결과 조회 API는 판정, 의심도, 최대 3개 참고 구간, 안내 문구를 반환한다.

### Edge Cases

| ID | 상황 | 처리 |
|---|---|---|
| EC-01 | 모델 파일 없음 | health는 정상, model-status는 `loading` 또는 `error`, analyze는 `503 MODEL.NOT_READY` |
| EC-02 | 지원하지 않는 확장자 | `400 REQUEST.UNSUPPORTED_FORMAT` |
| EC-03 | 확장자는 맞지만 음성이 아니거나 손상됨 | `400 AUDIO.INVALID` |
| EC-04 | IP 요청 제한 초과 | `429 SERVICE.RATE_LIMITED` |
| EC-05 | 같은 IP에 작업 진행 중 | `409 JOB.ALREADY_RUNNING` |
| EC-06 | STT 언어가 한국어가 아님 | 작업 `failed`, `STT.NON_KOREAN` |
| EC-07 | 사용자 취소 | 작업 `cancelled`, 결과 폐기, 임시자료 삭제 |
| EC-08 | 존재하지 않는 job_id | `404 JOB.NOT_FOUND` |
| EC-09 | 이미 완료된 작업 취소 | `409 JOB.ALREADY_FINISHED` |
| EC-10 | 모델·STT·분류 런타임 실패 | 작업 `failed`, 내부 내용은 로그에 남기지 않고 공통 오류 응답 |

## How

### API

모든 경로는 `/api/v1` prefix를 사용한다.

| Method | Path | 역할 |
|---|---|---|
| GET | `/api/v1/health` | 서버 응답 가능 여부만 확인; 모델 로드 여부와 분리 |
| GET | `/api/v1/model-status` | STT·분류 모델 상태 확인 |
| POST | `/api/v1/analyze` | multipart `audio` 업로드 및 작업 생성 |
| GET | `/api/v1/analyze/{job_id}/status` | 현재 작업 상태와 stage 조회 |
| GET | `/api/v1/analyze/{job_id}/result` | 완료 결과 조회 |
| DELETE | `/api/v1/analyze/{job_id}` | 작업 취소와 결과 폐기 |

작업 상태는 `queued`, `running`, `completed`, `failed`, `cancelled`이고, stage는 `queued`, `preprocessing`, `transcribing`, `classifying`, `finalizing`, `completed`이다.

### Audio and pipeline

- 입력 확장자: `wav`, `mp3`, `m4a`
- 전처리 기준: mono / 16kHz / 16-bit signed PCM
- 오디오 청크: 30초, 오버랩 10%
- 텍스트 분류용 토큰 청킹(256/64)은 오디오 청킹과 별도이며 classifier adapter 책임으로 둔다.
- STT는 Faster-Whisper adapter, 분류는 ONNX Runtime adapter로 격리한다.
- 언어가 한국어가 아니면 분석을 실패시킨다.
- 결과는 통화 단위로 집계하고 의심 참고 구간은 최대 3개로 제한한다.

### State, security, cleanup

- MVP는 단일 FastAPI 인스턴스의 메모리 registry와 background task runner를 사용한다.
- IP 원문은 저장하지 않고 환경변수 secret으로 해시한 키만 rate limit·중복 잠금에 사용한다.
- 작업 종료(성공·실패·취소)와 예외 경로에서 원본 음성, 전사문, 중간 결과, 임시파일을 삭제한다.
- 서버 재시작으로 registry가 사라지는 것은 MVP 제약이며, DB·외부 큐는 포함하지 않는다.
- 로그에는 음성 내용·전사문·개인정보·인증정보를 기록하지 않는다.

### Error response

```json
{
  "request_id": "req_123",
  "error_code": "MODEL.NOT_READY",
  "stage": "model_check",
  "message": "분석 모델이 아직 준비되지 않았습니다.",
  "retryable": true
}
```

## AC (Given-When-Then)

### AC-01 · 모델 미준비 상태

- **Given**: STT 또는 분류 모델 경로가 없거나 로딩 실패
- **When**: health, model-status, analyze를 각각 호출
- **Then**: health는 `200`, model-status는 `loading` 또는 `error`, analyze는 `503 MODEL.NOT_READY`

### AC-02 · 작업 생성과 상태 조회

- **Given**: fake analyzer가 준비되고 유효한 음성파일이 업로드됨
- **When**: analyze를 호출하고 job status를 반복 조회
- **Then**: `202`와 job_id를 받고 모든 stage를 거쳐 completed가 된다.

### AC-03 · 결과 계약

- **Given**: 작업이 completed 상태
- **When**: result를 호출
- **Then**: label, score, 최대 3개 segments, advice가 반환되고 음성 원문은 저장되지 않는다.

### AC-04 · 입력 검증

- **Given**: 잘못된 확장자 또는 손상·비음성 파일
- **When**: analyze를 호출
- **Then**: 작업을 만들지 않고 명시적 4xx 오류를 반환한다.

### AC-05 · 취소와 정리

- **Given**: queued 또는 running 작업
- **When**: DELETE를 호출
- **Then**: 작업은 cancelled가 되고 result 조회는 실패하며 임시자료와 잠금이 정리된다.

### AC-06 · 중복 및 rate limit

- **Given**: 같은 IP에 진행 중인 작업 또는 제한 횟수 초과 상태
- **When**: 새 analyze를 호출
- **Then**: 각각 `409 JOB.ALREADY_RUNNING` 또는 `429 SERVICE.RATE_LIMITED`를 반환한다.

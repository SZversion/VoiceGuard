# Spec — 모델 연결 전 백엔드 API와 분석 작업 구조

## Why

- **페르소나**: Nuxt.js 프론트엔드 담당자, STT·분류 파이프라인 담당자, FastAPI 백엔드 담당자
- **상황**: 프론트엔드는 업로드·진행 상태·결과 화면을 개발해야 하지만, 파인튜닝 모델과 최종 모델 설정은 아직 전달되지 않았다.
- **문제**:
  1. 백엔드 API 계약이 없으면 프론트엔드가 실제 요청·응답 형식에 맞춰 개발할 수 없다.
  2. 모델 연결 코드와 작업 상태 관리가 섞이면 모델 교체 시 API와 배포 코드까지 함께 변경될 수 있다.
  3. 음성·전사·중간 결과를 성공·실패·취소 후 확실히 삭제할 공통 정리 흐름이 필요하다.
- **측정 지표**: Swagger에서 정의된 모든 API 확인, 상태 전이·취소·임시자료 삭제 자동 테스트 통과, Railway 환경에서 `/api/health` 응답 확인

## Goal

- Nuxt.js가 연동할 `/api` API 계약을 정의한다.
- FastAPI 서버, 모델 상태, 메모리 기반 작업 레지스트리, 취소, 오류 응답과 정리 책임을 분리한다.
- 모델이 없는 상태에서는 분석 결과를 임의 생성하지 않고 `MODEL.NOT_READY` 오류를 반환한다.
- 모델 전달 후 STT·분류 연결부를 교체할 수 있는 파일 경계를 정의한다.
- Railway에서 `0.0.0.0:$PORT`로 실행하고 Swagger `/docs`를 제공한다.

### 성공 기준

- `/api/health`는 모델을 로드하지 않고 서버 상태를 반환한다.
- `/api/model-status`는 `loading`, `ready`, `error` 중 하나를 반환한다.
- 분석 생성·상태·결과·취소 API의 요청과 응답 형식이 Swagger에 표시된다.
- 성공·실패·취소 흐름에서 원본 음성, 전사문, 중간 결과가 남지 않는다.
- 모델 미연결 상태의 분석 요청은 HTTP 503과 `MODEL.NOT_READY`를 반환한다.

### Out of Scope

- 모델 이름 또는 Hugging Face 저장소 결정
- 파인튜닝, ONNX 변환 또는 모델 성능 수치 결정
- 청크 크기·겹침, threshold, 통화 점수 집계 방식 결정
- 데이터베이스, 회원가입, 분석 이력 저장
- 프론트엔드 화면과 Streamlit 화면 구현
- 실제 또는 가짜 모델 결과를 운영 API에서 생성

## What

### Happy Path

1. 서버 시작 시 환경변수와 STT·분류 모델 설정을 확인한다.
2. 모델이 없으면 모델 상태를 `loading` 또는 `error`로 유지한다.
3. 프론트엔드는 `GET /api/health`로 서버 응답 가능 여부를 확인한다.
4. 프론트엔드는 `GET /api/model-status`로 두 모델의 준비 상태를 확인한다.
5. 사용자는 `POST /api/analyze`에 `.wav`, `.mp3`, `.m4a` 파일 하나를 업로드한다.
6. 서버는 확장자, 실제 형식, 손상 여부, IP 요청 제한과 동일 사용자 중복 작업을 확인한다.
7. 서버는 임시파일과 `job_id`를 만들고 작업 상태를 `queued`로 기록한다.
8. 비동기 작업은 다음 단계 순서로 진행한다.

```text
queued
  ↓
preprocessing
  ├─ mono
  ├─ 16kHz
  └─ 16-bit PCM
  ↓
transcribing
  ├─ Faster-Whisper 실행
  └─ 한국어가 아니면 실패 처리
  ↓
classifying
  ├─ 음성데이터 청킹
  └─ ONNX 분류 모델로 청크별 점수 계산
  ↓
finalizing
  ├─ 통화 전체 점수 계산
  ├─ 정상/보이스피싱 의심 판정
  └─ 의심 구간 최대 3개 선정
  ↓
completed
```

9. 프론트엔드는 상태 API를 주기적으로 호출하고 완료 후 결과 API를 호출한다.
10. 서버는 성공·실패·취소 모두에서 원본 음성, 전사문과 중간 결과를 삭제하고 사용자 잠금을 해제한다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 모델 미준비 상태에서 분석 요청 | HTTP 503과 `MODEL.NOT_READY` 반환, 파일 잔존 금지 |
| EC-02 | 지원하지 않는 확장자 또는 실제 형식 | 요청 거절 후 임시자료 삭제 |
| EC-03 | 손상 파일 또는 음성 스트림 없음 | 오디오 오류 응답 후 임시자료 삭제 |
| EC-04 | 한국어가 아닌 음성 | STT 단계 실패 처리 후 임시자료 삭제 |
| EC-05 | 같은 사용자의 작업이 이미 진행 중 | 중복 작업 오류 반환, 기존 작업 유지 |
| EC-06 | IP 요청 제한 초과 | `SERVICE.RATE_LIMITED` 반환 |
| EC-07 | 존재하지 않는 `job_id` 조회 | 작업 없음 오류 반환 |
| EC-08 | 진행 중 작업 취소 | `cancelled` 기록, 결과 폐기, 가능한 가장 빠른 시점에 중단 |
| EC-09 | 완료 작업 취소 | 완료 결과를 유지하고 취소 불가 응답 |
| EC-10 | 분석 도중 예외 발생 | `failed` 기록, 사용자용 오류 반환, 임시자료 삭제와 잠금 해제 |

## How

### API 계약

| Method | Path | 역할 |
|---|---|---|
| GET | `/api/health` | API 서버 상태 확인 |
| GET | `/api/model-status` | STT·분류 모델 준비 상태 확인 |
| POST | `/api/analyze` | 음성 분석 작업 생성 및 `job_id` 반환 |
| GET | `/api/analyze/{job_id}/status` | 현재 작업 상태와 단계 반환 |
| GET | `/api/analyze/{job_id}/result` | 완료된 분석 결과 반환 |
| DELETE | `/api/analyze/{job_id}` | 작업 취소와 결과 폐기 |

분석 업로드는 `multipart/form-data`의 `audio` 필드를 사용한다. 작업 상태는 `queued`, `running`, `completed`, `failed`, `cancelled`를 사용하고 처리 단계는 `queued`, `preprocessing`, `transcribing`, `normalizing`, `classifying`, `risk_search`, `finalizing`, `completed`, `failed`, `cancelled`를 사용한다.

오류 응답은 PRD의 공통 구조를 따른다.

```json
{
  "request_id": "req_12345",
  "error_code": "MODEL.NOT_READY",
  "stage": "model_loading",
  "message": "분석 모델이 아직 준비되지 않았습니다.",
  "retryable": true
}
```

### 파일구조

```text
proj1-e/
├─ app/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ routes/
│  │  │  ├─ health.py
│  │  │  └─ analyze.py
│  │  ├─ schemas.py
│  │  └─ errors.py
│  ├─ analysis/
│  │  ├─ pipeline.py
│  │  ├─ audio.py
│  │  ├─ stt.py
│  │  ├─ classifier.py
│  │  ├─ aggregation.py
│  │  └─ cleanup.py
│  ├─ jobs/
│  │  ├─ registry.py
│  │  └─ runner.py
│  └─ core/
│     ├─ config.py
│     ├─ security.py
│     └─ rate_limit.py
├─ tests/
│  ├─ api/
│  ├─ analysis/
│  └─ jobs/
├─ docs/specs/backend-api.md
├─ requirements.txt
├─ .env.example
└─ Dockerfile
```

### 책임과 제약

- `app/api`는 HTTP 계약과 오류 응답만 담당한다.
- `app/jobs`는 메모리 기반 작업 상태, 비동기 실행과 취소를 담당한다.
- `app/analysis`는 화면과 API에 의존하지 않는 공통 분석 흐름을 담당한다.
- `app/core`는 Railway 환경변수, IP 해시와 요청 제한을 담당한다.
- CORS는 `http://localhost:3000`과 환경변수로 전달되는 배포 Nuxt URL만 허용한다.
- Railway 실행 명령은 `0.0.0.0:$PORT`를 사용한다.
- Hugging Face 토큰이 필요하면 Railway 환경변수에만 저장하고 프론트엔드·로그·저장소에 노출하지 않는다.
- 테스트의 대체 분석기는 테스트 코드 안에서만 사용하고 운영 API에서는 가짜 결과를 반환하지 않는다.
- 음성데이터 청킹의 정확한 위치·입력 형식·크기·겹침은 모델·파이프라인 전달 자료로 검증한 뒤 별도 승인 없이 구현하지 않는다.

## AC (Given-When-Then)

### AC-01 · 서버 상태 확인

- **GIVEN**: FastAPI 서버가 실행 중이다.
- **WHEN**: 프론트엔드가 `GET /api/health`를 호출한다.
- **THEN**: 모델 로드 여부와 무관하게 HTTP 200과 서버 상태를 반환한다.

### AC-02 · 모델 상태 확인

- **GIVEN**: STT 또는 분류 모델이 준비되지 않았다.
- **WHEN**: `GET /api/model-status`를 호출한다.
- **THEN**: HTTP 200과 `loading` 또는 `error` 상태를 반환하고 분석 가능 상태로 표시하지 않는다.

### AC-03 · 모델 미준비 분석 거절

- **GIVEN**: 하나 이상의 모델이 준비되지 않았다.
- **WHEN**: 지원 형식의 음성파일로 `POST /api/analyze`를 호출한다.
- **THEN**: HTTP 503과 `MODEL.NOT_READY`를 반환하고 업로드 파일을 남기지 않는다.

### AC-04 · 작업 상태 조회

- **GIVEN**: 테스트 대체 분석기로 생성한 작업이 진행 중이다.
- **WHEN**: `GET /api/analyze/{job_id}/status`를 호출한다.
- **THEN**: 정의된 `status`와 현재 `stage`만 반환하고 음성·전사 내용을 포함하지 않는다.

### AC-05 · 완료 결과 조회

- **GIVEN**: 테스트 대체 분석기로 작업이 완료됐다.
- **WHEN**: `GET /api/analyze/{job_id}/result`를 호출한다.
- **THEN**: 라벨, 의심도, 최대 3개 참고 구간과 안내 문구를 계약에 맞춰 반환한다.

### AC-06 · 작업 취소와 정리

- **GIVEN**: 작업이 완료되지 않고 진행 중이다.
- **WHEN**: `DELETE /api/analyze/{job_id}`를 호출한다.
- **THEN**: 상태를 `cancelled`로 바꾸고 결과를 폐기하며 임시자료를 삭제하고 사용자 잠금을 해제한다.

### AC-07 · 실패 시 정리

- **GIVEN**: 전처리, STT, 분류 또는 결과 정리 단계에서 예외가 발생한다.
- **WHEN**: 작업 실행기가 예외를 처리한다.
- **THEN**: 상태를 `failed`로 바꾸고 공통 오류 응답을 기록하며 음성·전사·중간 결과를 삭제하고 사용자 잠금을 해제한다.

### AC-08 · Railway 실행

- **GIVEN**: Railway가 `PORT` 환경변수를 제공한다.
- **WHEN**: 배포 시작 명령을 실행한다.
- **THEN**: FastAPI가 `0.0.0.0:$PORT`에서 실행되고 `/docs`와 `/api/health`에 접근할 수 있다.


## Analysis progress contract

The job status response keeps the existing `job_id`, `status`, and `stage` fields and adds an integer `progress` from 0 to 100.

| Stage | Progress |
|---|---:|
| queued | 0 |
| preprocessing | 10 |
| transcribing | 30 |
| normalizing | 45 |
| classifying | 65 |
| risk_search | 80 |
| finalizing | 90 |
| completed | 100 |

Progress is monotonic during a running job. Failed and cancelled jobs do not advance to completed.

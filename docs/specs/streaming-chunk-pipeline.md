# Streaming Chunk Pipeline

## Why

현재 분석은 모든 30초 음성 청크의 STT가 끝난 뒤 분류를 시작한다. 이 구조에서는 STT가 끝날 때까지 분류 모델이 대기하고, 분류 단계의 진행률이 첫 번째 청크 이후 멈춘 것처럼 보일 수 있다.

## Goal

- STT가 완료한 청크를 순서대로 분류 파이프라인에 전달한다.
- STT와 분류가 가능한 범위에서 겹쳐 실행되도록 한다.
- 상태 API에서 전사·정규화·분류 완료 청크 수와 전체 청크 수를 반환한다.
- 분류 단계의 진행률을 전체 청크 수 기준으로 65~80 범위에서 증가시킨다.
- producer 또는 consumer 실패 시 남은 task를 정리하고 기존 분석 실패 계약을 유지한다.

Out of scope:

- 실시간 통화 중 분석
- 청크별 별도 public API
- 기존 결과 형식의 변경

## What

### Happy Path

1. 오디오를 30초 단위 청크로 나눈다.
2. Whisper producer가 청크 하나의 전사를 완료할 때마다 bounded queue에 넣는다.
3. classifier consumer는 queue에서 받은 청크를 정규화한 뒤 ONNX INT8 분류를 수행한다.
4. 상태 API는 `progress_details`에 다음 값을 반환한다.
   - `transcribed_chunks`
   - `normalized_chunks`
   - `classified_chunks`
   - `total_chunks`
5. 모든 청크가 처리되면 기존 상위 5개 평균 점수와 상위 3개 근거 구간을 반환한다.

### Edge Case

- STT가 예외를 발생시키면 consumer task를 취소하고 분석을 실패 처리한다.
- 분류가 예외를 발생시키면 producer task를 취소하고 분석을 실패 처리한다.
- 청크가 없으면 분석을 실패 처리한다.
- 기존 `transcribe_chunks`만 제공하는 transcriber는 기존 순차 경로를 사용한다.

## How

- `WhisperTranscriber.transcribe_chunks_stream`는 `(index, total, TranscriptChunk)`를 async generator로 yield한다.
- analyzer는 `asyncio.Queue(maxsize=1)`로 producer와 consumer 사이의 backpressure를 유지한다.
- blocking ONNX inference는 `asyncio.to_thread`로 실행해 event loop를 막지 않는다.
- `JobRunner`는 `report_progress` callback으로 `JobRegistry.metadata`와 진행률을 갱신한다.
- status 응답에 `progress_details`를 조건부로 추가해 기존 metadata가 없는 응답 계약을 유지한다.

## AC

### AC1 — 청크 스트리밍

Given 3개의 오디오 청크를 생성하는 transcriber가 있을 때
When analyzer를 실행하면
Then 각 청크가 전사 완료 후 분류 입력으로 전달되고 최종 결과가 생성된다.

### AC2 — 청크 진행률

Given 3개 중 1개만 분류 완료된 작업일 때
When status API를 조회하면
Then `progress_details.classified_chunks`가 1이고 `total_chunks`가 3이며 진행률이 65보다 크다.

### AC3 — 실패 task 정리

Given producer가 첫 청크 후 예외를 발생시킬 때
When analyzer가 실행되면
Then producer 예외가 호출자에게 전달되고 consumer가 pending 상태로 남지 않는다.

### AC4 — 기존 계약 호환

Given progress metadata가 없는 작업일 때
When status API를 조회하면
Then 기존 `job_id`, `status`, `stage`, `progress` 필드만 반환한다.
# Spec — Faster-Whisper STT adapter 연결

## Why

- **페르소나**: 음성 파일 분석 API를 사용하는 사용자와 백엔드 파이프라인 담당자
- **상황**: 현재 `VoicePhishingAnalyzer`는 `Transcriber`를 주입받을 수 있지만, 실제 음성 파일을 한국어 transcript로 변환하는 runtime 구현이 없다.
- **문제**:
  1. 업로드된 음성 bytes를 STT 모델 입력으로 전달할 구현이 없다.
  2. 한국어가 아닌 음성을 분석 파이프라인에서 중단할 기준이 없다.
  3. STT 모델 로딩 실패와 추론 실패를 테스트 가능한 상태로 표현할 경계가 없다.
- **측정 지표**: 모델 로딩 상태 기록, 한국어 transcript 생성 성공 여부, 비한국어 입력 거절 여부, 임시파일 정리 여부, 실제 모델 다운로드 없는 단위 테스트 실행 가능 여부

## Goal

- Faster-Whisper CTranslate2 모델을 앱 시작 시 한 번 로드할 수 있다.
- `Transcriber` 계약에 맞는 adapter가 `audio: bytes`를 받아 한국어 transcript를 반환한다.
- CPU `int8` 실행을 기본 설정으로 사용하고 모델 크기·device·compute type을 환경변수로 변경할 수 있다.
- STT가 한국어가 아니거나 transcript가 비어 있으면 명시적인 STT 오류를 발생시킨다.
- 모델 로딩·추론 테스트는 실제 Hugging Face 모델 다운로드 없이 실행할 수 있다.

**성공 기준**

- loader가 주입된 factory를 한 번 호출하고 모델 초기화 오류를 `STTModelLoadError`로 변환한다.
- adapter가 정상 입력에서 transcript 문자열을 반환한다.
- adapter가 `language != "ko"`인 결과를 `UnsupportedLanguageError`로 변환한다.
- adapter가 임시 입력 파일을 사용한 경우 성공·실패와 관계없이 삭제한다.
- 테스트 명령으로 STT 관련 단위 테스트를 재현할 수 있다.

**Out of Scope**

- STT 모델 재학습 또는 LoRA fine-tuning
- FFmpeg/librosa/torchaudio 기반 전처리 파이프라인의 구현
- transcript 청킹, 통화 단위 집계, 보이스피싱 분류
- `VoicePhishingAnalyzer`를 FastAPI app state에 연결하는 작업
- 실시간 스트리밍 STT
- CER/WER 성능 측정 및 모델 품질 보증

## What

### Happy Path

1. 앱 초기화가 Faster-Whisper model factory를 호출한다.
2. factory는 환경설정에 따라 CPU `int8` 모델을 반환한다.
3. `FasterWhisperTranscriber.transcribe(audio)`가 bytes를 임시 입력으로 준비한다.
4. Whisper 모델이 음성을 전사하고 언어 정보를 반환한다.
5. 언어가 `ko`이고 transcript가 비어 있지 않으면 transcript를 반환한다.
6. 임시 입력은 분석 성공 여부와 관계없이 삭제한다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | STT 모델 로딩 실패 | `STTModelLoadError`로 변환하고 runtime 상태를 `error`로 기록 |
| EC-02 | 빈 audio bytes | 모델 호출 전 `AudioInputError` 발생 |
| EC-03 | 모델 결과 언어가 한국어가 아님 | `UnsupportedLanguageError` 발생 |
| EC-04 | 언어 정보가 없거나 감지 실패 | `UnsupportedLanguageError` 발생 |
| EC-05 | 전사 segment가 없거나 transcript가 공백 | `TranscriptionError` 발생 |
| EC-06 | 모델 추론 중 예외 | `TranscriptionError`로 변환하고 임시 입력 삭제 |
| EC-07 | 테스트에서 실제 모델을 사용할 수 없음 | factory/model/segments를 주입하여 다운로드 없이 검증 |
| EC-08 | 긴 음성 파일 | 이번 단계에서는 길이 제한을 추가하지 않고, 처리 시간·메모리는 후속 평가에서 측정 |

## How

### 파일 경계

`@text
app/analysis/stt.py
  ├─ STT 설정과 예외 타입
  ├─ FasterWhisperTranscriber adapter
  └─ 모델 출력에서 transcript/language 추출

app/analysis/stt_loader.py
  └─ Faster-Whisper model factory와 로딩 오류 변환

tests/analysis/test_stt.py
tests/analysis/test_stt_loader.py
  └─ fake model/factory를 이용한 deterministic unit test
`@

### Runtime 설정

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `STT_MODEL_SIZE` | `small` | Faster-Whisper 모델 크기 |
| `STT_DEVICE` | `cpu` | 실행 device |
| `STT_COMPUTE_TYPE` | `int8` | CPU 양자화 실행 형식 |
| `STT_LANGUAGE` | `ko` | 허용 언어 |

모델은 앱 startup에서 한 번만 로드한다. 테스트는 loader factory를 주입하여 네트워크와 모델 다운로드를 차단한다.

### Transcriber 계약

`@python
class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        ...
`@

adapter는 기존 `VoicePhishingAnalyzer`의 계약을 변경하지 않는다. Faster-Whisper의 동기 추론은 adapter 내부에서 실행하며, async analyzer를 차단하지 않도록 구현 시 실행 경계를 별도로 검토한다.

### 오류 계약

이번 단계의 내부 예외는 다음 의미를 갖는다.

- `STTModelLoadError`: 모델 초기화 실패
- `AudioInputError`: 입력 bytes가 비어 있음
- `UnsupportedLanguageError`: 한국어가 아닌 음성 또는 언어 감지 실패
- `TranscriptionError`: 전사 결과가 없거나 추론 실패

API error code 매핑과 `POST /api/analyze`의 HTTP 응답 연결은 analyzer runtime wiring 단계에서 정의한다.

## AC

### AC-01 · 모델 로더 성공

- **GIVEN**: 테스트용 model factory가 정상 모델을 반환한다.
- **WHEN**: STT loader를 호출한다.
- **THEN**: factory 설정값으로 생성된 transcriber를 반환한다.

### AC-02 · 모델 로더 실패

- **GIVEN**: model factory가 예외를 발생시킨다.
- **WHEN**: STT loader를 호출한다.
- **THEN**: `STTModelLoadError`가 발생한다.

### AC-03 · 한국어 전사 성공

- **GIVEN**: fake Whisper model이 `language="ko"`와 하나 이상의 segment를 반환한다.
- **WHEN**: adapter에 비어 있지 않은 audio bytes를 전달한다.
- **THEN**: segment text를 합친 transcript 문자열을 반환한다.

### AC-04 · 비한국어 음성 거절

- **GIVEN**: fake Whisper model이 `language="en"`을 반환한다.
- **WHEN**: adapter가 전사를 수행한다.
- **THEN**: `UnsupportedLanguageError`가 발생한다.

### AC-05 · 빈 전사 거절

- **GIVEN**: 모델이 한국어라고 보고하지만 segment text가 공백이다.
- **WHEN**: adapter가 전사를 수행한다.
- **THEN**: `TranscriptionError`가 발생한다.

### AC-06 · 입력 검증

- **GIVEN**: audio bytes가 비어 있다.
- **WHEN**: adapter가 전사를 수행한다.
- **THEN**: 모델을 호출하지 않고 `AudioInputError`가 발생한다.

### AC-07 · 임시 입력 정리

- **GIVEN**: adapter가 성공하거나 추론 중 예외가 발생한다.
- **WHEN**: 전사 처리가 종료된다.
- **THEN**: adapter가 생성한 임시 입력이 삭제된다.

### AC-08 · 테스트 격리

- **GIVEN**: STT 단위 테스트를 실행한다.
- **WHEN**: fake factory와 fake model을 주입한다.
- **THEN**: 외부 네트워크나 실제 모델 다운로드 없이 테스트가 통과한다.
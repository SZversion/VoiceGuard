# STT 전사 품질 필터

## Why

- **페르소나**: 음성 통화 분석 결과를 확인하는 사용자와 STT·분류 파이프라인 담당자
- **상황**: 저음질·무음·잡음 구간에서 STT가 의미 없는 문자열을 반환할 수 있다.
- **문제**: 깨진 전사를 분류기에 전달하면 오분류가 증가하고 사용자가 잘못된 분석 결과를 신뢰할 수 있다.
- **측정 지표**: 품질 제외 건수, 제외 사유별 건수, 분류 호출 차단 건수, 정상 전사의 오제외 건수

## Goal

- 심하게 깨진 전사를 분류 입력에서 제외하고 명시적인 품질 상태를 반환한다.
- raw/corrected 전사는 보존하며 삭제하거나 덮어쓰지 않는다.
- **성공 기준**: 빈 전사·비정상 반복·유효 문자 비율 부족 전사는 분류기를 호출하지 않는다.
- **Out of Scope**: 일반 맞춤법 교정, 의미 기반 복원, LLM 기반 품질 판정, 음성 재생성

## What

### Happy Path

1. STT가 raw 전사를 반환한다.
2. 도메인 오탈자 교정을 적용한다.
3. 품질 필터가 corrected 전사를 검사한다.
4. 사용 가능한 전사만 분류기에 전달한다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 빈 전사 | `unusable` 상태와 `empty_transcript` 사유 반환 |
| EC-02 | 한 음절·토큰 반복 | `unusable` 상태와 `repeated_tokens` 사유 반환 |
| EC-03 | 유효 문자 비율 부족 | `unusable` 상태와 `low_valid_ratio` 사유 반환 |
| EC-04 | 정상적인 짧은 금융 표현 | 길이만으로 무조건 제외하지 않고 유효 토큰이면 유지 |
| EC-05 | 품질 제외 | raw/corrected 전사는 보존하고 classifier는 호출하지 않음 |

## How

- `TranscriptQualityFilter`는 순수 문자열 검사 객체로 둔다.
- 검사 결과는 `usable`, `score`, `reason`을 반환한다.
- 기본 검사 기준:
  - 공백 제거 후 비어 있으면 제외
  - 한글·숫자·기본 문장부호 외 문자의 비율이 40% 초과하면 제외
  - 동일 토큰이 전체 토큰의 70% 이상이며 토큰 수가 4개 이상이면 제외
  - 한글 또는 숫자를 포함하는 토큰이 없으면 제외
- 분석기는 품질 제외 시 `label`과 `suspicion_score`를 생성하지 않고 `classification_status="skipped"`와 `quality`를 반환한다.
- 음성 원본·전체 녹취문은 평가 결과 파일에 저장하지 않는다.

## AC

### AC-01 · 빈 전사 제외

- **Given**: corrected 전사가 공백이다.
- **When**: 품질 필터를 실행한다.
- **Then**: `usable=false`, 사유는 `empty_transcript`이다.

### AC-02 · 깨진 반복 전사 제외

- **Given**: 동일 토큰이 비정상적으로 반복된다.
- **When**: 분석을 실행한다.
- **Then**: classifier를 호출하지 않고 `classification_status="skipped"`를 반환한다.

### AC-03 · 정상 전사 통과

- **Given**: 의미 있는 한국어 금융 문장이 있다.
- **When**: 품질 필터를 실행한다.
- **Then**: `usable=true`이고 classifier가 corrected 전사를 받는다.

### AC-04 · 원문 보존

- **Given**: 품질 필터가 전사를 제외한다.
- **When**: 분석 결과를 생성한다.
- **Then**: `raw_transcript`와 `corrected_transcript`는 그대로 반환된다.

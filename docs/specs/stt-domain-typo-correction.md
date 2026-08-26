# STT 도메인 용어 오탈자 교정

## Why

- **페르소나**: 한국어 통화 음성을 분석하고 보이스피싱 분류 결과를 확인하는 사용자와 STT·분류 파이프라인 담당자
- **상황**: 전화망 품질 음성의 STT 결과에서 금융·수사·보이스피싱 관련 용어가 띄어쓰기나 표기 변형으로 생성될 수 있다.
- **문제**: 도메인 용어가 분류 모델의 입력에서 깨지면 위험 표현 인식과 보이스피싱 분류 결과가 흔들릴 수 있다. 반대로 일반 맞춤법 교정을 무제한 적용하면 구어체·고유명사·정상 금융상담 문장을 잘못 바꿀 수 있다.
- **측정 지표**: raw 전사와 교정 전사의 CER/WER 변화, 통화 단위 Recall·FNR·FPR·Precision·F1 변화, 교정 건수, 오교정 건수, 교정으로 분류 결과가 변경된 건수

## Goal

- 명시적인 허용 교정 테이블만 사용해 금융·수사·보이스피싱 도메인 용어의 오탈자를 보수적으로 자동 교정한다.
- 띄어쓰기 변형은 규칙에 보관할 수 있지만 기본 자동 교정 대상에서 제외한다.
- 원문 전사(`raw_transcript`)를 보존하고, 별도 교정 전사(`corrected_transcript`)를 생성한다.
- 교정 전사를 보이스피싱 분류기의 입력으로 사용한다.
- 각 교정의 원문·교정문·규칙 식별자를 결과에 기록한다.
- 동일한 통화 단위 평가 세트에서 raw 입력과 corrected 입력의 성능을 비교할 수 있게 한다.
- Out of Scope:
  - 일반 한국어 맞춤법·띄어쓰기 전체 교정
  - 의미 기반 문장 재작성
  - LLM 또는 외부 교정 API 사용
  - 음성 원본을 참고한 사후 정답 맞춤 교정
  - 교정 결과를 raw 전사 위에 덮어쓰기

## What

### Happy Path

1. STT가 한국어 전사문을 반환한다.
2. 도메인 교정기가 전사문에 허용된 규칙을 순서대로 적용한다.
3. 교정기는 원문, 교정문, 적용된 교정 목록을 반환한다.
4. 분석기는 `corrected_transcript`를 텍스트 분류기에 전달한다.
5. 분석 결과에는 raw 전사, corrected 전사, 교정 목록과 기존 분류 결과가 함께 포함된다.

### Edge Cases

| ID | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 허용 목록에 없는 표현 | 교정하지 않고 원문을 유지한다. |
| EC-02 | 같은 문장에 여러 규칙이 적용됨 | 명시된 규칙 순서대로 적용하고 각 적용 내역을 기록한다. |
| EC-03 | 한 규칙이 다른 규칙의 입력을 생성함 | 규칙 테이블에서 순서를 고정하고 테스트로 결과를 검증한다. |
| EC-04 | 원문과 교정문이 동일함 | `corrections`는 빈 목록으로 반환한다. |
| EC-05 | 교정 후 공백만 남음 | 분류기 호출 전에 명시적인 빈 전사 오류로 처리한다. |
| EC-06 | 정상 금융상담 표현이 교정 대상과 부분 일치함 | 단어 경계 또는 가장 구체적인 표현 우선 규칙으로 불필요한 부분 교정을 방지한다. |
| EC-07 | 교정 규칙 설정이 잘못됨 | 앱 시작 또는 교정기 생성 시 검증 오류를 발생시키며 조용히 무시하지 않는다. |
| EC-08 | 교정으로 분류 결과가 달라짐 | raw/corrected 입력과 결과를 평가 로그에 남기고, 모델 결과를 법적·수사적 확정 판정으로 표현하지 않는다. |

## How

### 처리 경계

```text
Transcriber
  -> raw_transcript
  -> DomainTermCorrector
  -> corrected_transcript
  -> TextClassifier
```

`VoicePhishingAnalyzer`는 전사 결과를 직접 분류기에 전달하지 않고, 주입된 교정기를 통해 corrected 전사를 만든다. 교정기는 STT나 분류 모델을 알지 않으며, 순수한 문자열 변환과 교정 내역 생성을 담당한다.

### 제안 파일 경계

- `app/analysis/domain_corrector.py`
  - 교정 규칙 자료형
  - 허용 교정 테이블 검증
  - 순서가 보장된 exact phrase 교정
  - 교정 결과와 적용 내역 반환
- `app/analysis/analyzer.py`
  - 교정기 주입
  - corrected 전사를 분류기에 전달
  - raw/corrected 전사와 교정 내역을 분석 결과에 포함
- `app/api/schemas.py` 또는 결과 전용 Schema 파일
  - API 결과의 전사·교정 필드 타입 정의
- `data/stt_dictionary/domain_corrections.json` 또는 Python 상수
  - 사람이 검토한 도메인 교정 규칙 관리
- `tests/analysis/test_domain_corrector.py`
  - 교정 규칙과 edge case 단위 테스트
- `tests/analysis/test_analyzer.py`
  - corrected 전사가 classifier에 전달되는지 검증
- `docs/specs/stt-domain-typo-correction.md`
  - 본 기능의 범위와 AC

기존 `data/stt_dictionary/vocabulary.txt`는 인식 후보 용어 목록으로 유지하고, 실제 치환 규칙은 별도 테이블로 분리한다. 단순히 어휘 목록에 단어를 추가하는 것만으로 원문을 자동 수정하지 않는다.

### 교정 규칙

초기 규칙은 다음 조건을 모두 만족해야 한다.

- 금융·수사·보이스피싱 도메인과 직접 관련된다.
- 사람이 교정 결과를 확인할 수 있다.
- exact phrase 또는 안전한 경계 조건으로 적용할 수 있다.
- 필요한 규칙은 source 주변의 제한된 문맥 키워드와 검색 범위를 함께 요구한다.
- 원문을 정답 데이터와 비교해 역으로 만든 규칙이 아니다.

규칙에는 최소한 다음 정보를 둔다. `kind`는 `typo` 또는 `spacing`이며, 기본 교정기는 `typo`만 활성화한다.

```json
{
  "id": "domain-financial-001",
  "source": "대출 상환",
  "target": "대출상환",
  "reason": "금융 용어 표기 교정",
  "kind": "spacing",
  "context_terms": [],
  "context_window": 20
}
```

일반 맞춤법 교정은 이번 단계에서 적용하지 않는다. 띄어쓰기 규칙도 기본 자동 교정에서는 제외한다. 후속 단계에서 활성화하더라도 domain 교정과 별도 stage로 두고 raw/domain/general 세 결과를 비교할 수 있어야 한다.

### API 결과 예시

```json
{
  "raw_transcript": "검찰 청을 사칭한 사람이 대출 상환을 요구했습니다.",
  "corrected_transcript": "검찰청을 사칭한 사람이 대출상환을 요구했습니다.",
  "corrections": [
    {
      "rule_id": "domain-investigation-001",
      "from": "검찰 청",
      "to": "검찰청",
      "reason": "수사기관명 표기 교정"
    }
  ],
  "label": "voice_phishing",
  "suspicion_score": 0.94,
  "reference_segments": [],
  "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요."
}
```

기존 API 소비자와의 호환성이 필요하면 새 필드는 optional로 추가하고, 기존 `label`, `suspicion_score`, `reference_segments`, `guidance` 계약은 유지한다.

### 평가

- 같은 통화 단위 train/validation/test 분할을 유지한다.
- 같은 STT 결과에 대해 raw와 corrected 두 입력을 만든다.
- 분류 성능은 Recall, FNR, FPR, Precision, F1을 함께 기록한다.
- STT 품질은 가능한 경우 CER과 WER를 기록한다.
- 정상 금융상담 hard negative와 저음질 음성을 별도 그룹으로 확인한다.
- 교정 규칙별 적용 횟수와 오교정 사례를 별도 검토한다.
- 검증하지 않은 개선 수치는 README나 발표자료에 기재하지 않는다.

### 개인정보·운영 제약

- 음성 원본과 전체 녹취문을 저장소에 커밋하지 않는다.
- 로그에는 전사문·개인정보를 남기지 않고, 필요하면 규칙 ID와 카운트만 기록한다.
- 분석 완료 후 임시 음성과 임시 녹취문을 삭제한다.

## AC

### AC-01 · 허용 규칙 교정

- **Given**: 전사문에 허용 교정 테이블의 source 표현이 포함되어 있다.
- **When**: 도메인 교정기를 실행한다.
- **Then**: 해당 source만 target으로 바뀌고 교정 내역에 rule ID가 기록된다.

### AC-02 · 미등록 표현 보존

- **Given**: 전사문에 허용 교정 테이블에 없는 표현이 포함되어 있다.
- **When**: 도메인 교정기를 실행한다.
- **Then**: 전사문 내용이 변경되지 않는다.

### AC-03 · 원문 보존

- **Given**: 하나 이상의 도메인 교정이 적용된다.
- **When**: 분석 결과를 생성한다.
- **Then**: `raw_transcript`는 STT 반환값과 동일하고 `corrected_transcript`만 교정된다.

### AC-04 · 분류 입력 교정본 사용

- **Given**: raw 전사와 corrected 전사가 서로 다르다.
- **When**: `VoicePhishingAnalyzer.analyze`를 실행한다.
- **Then**: classifier의 `classify`에는 corrected 전사가 전달된다.

### AC-05 · 교정 내역 반환

- **Given**: 여러 교정 규칙이 적용된다.
- **When**: 분석 결과를 생성한다.
- **Then**: 적용 순서에 맞는 각 교정의 source, target, reason, rule ID가 반환된다.

### AC-06 · 무변경 결과

- **Given**: 적용 가능한 교정 규칙이 없다.
- **When**: 도메인 교정기를 실행한다.
- **Then**: raw와 corrected가 동일하고 corrections는 빈 목록이다.

### AC-07 · 빈 교정 결과 거절

- **Given**: 교정 후 전사문이 공백이다.
- **When**: 분류 직전 검증을 수행한다.
- **Then**: classifier를 호출하지 않고 명시적인 빈 전사 오류를 반환한다.

### AC-08 · 규칙 검증

- **Given**: source가 비어 있거나 source와 target이 같거나 중복 규칙이 있다.
- **When**: 교정기를 생성한다.
- **Then**: 설정 오류를 발생시키고 잘못된 규칙을 등록하지 않는다.

### AC-09 · raw/corrected 평가 비교

- **Given**: 통화 단위로 분리된 평가 세트와 동일한 STT 결과가 있다.
- **When**: raw와 corrected 입력을 각각 평가한다.
- **Then**: 두 조건의 CER/WER 및 Recall·FNR·FPR·Precision·F1을 비교할 수 있는 결과가 생성된다.

### AC-10 · 오탈자 전용 기본 교정

- **Given**: `typo` 규칙과 `spacing` 규칙이 함께 등록되어 있다.
- **When**: 기본 설정으로 도메인 교정기를 실행한다.
- **Then**: `typo` 규칙만 적용되고 `spacing` 규칙은 원문에 유지된다.

### AC-11 · 문맥 조건 교정

- **Given**: 규칙에 문맥 키워드와 검색 범위가 설정되어 있다.
- **When**: 도메인 교정기를 실행한다.
- **Then**: 검색 범위 안에 키워드가 있는 source만 교정되고, 멀리 있는 source는 원문에 유지된다.

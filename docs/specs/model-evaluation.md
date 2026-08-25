# Spec - deployed model evaluation

## Why

모델이 Railway에서 실제 음성 입력을 처리하고도, 소수 샘플의 결과를 재현 가능한 지표로 비교할 수 있는 평가 절차가 필요하다. 음성파일은 검증 시점에만 사용하고 저장소에는 포함하지 않는다.

## Goal

실행자가 음성파일 경로와 기대 라벨을 별도로 제공하면 배포 API의 분석 결과를 수집하고 이진 분류 지표를 계산한다.

- 파일명으로 기대 라벨을 추론하지 않는다.
- `normal`과 `voice_phishing` 라벨을 명시적으로 검증한다.
- 작업 상태의 `stage`와 `progress`를 출력한다.
- 결과별 예측 라벨, 의심 점수, 근거 구간을 출력한다.
- Accuracy, Precision, Recall, F1, False Positive Rate를 계산한다.
- 음성 원본, 토큰, 결과 파일은 저장소에 커밋하지 않는다.

## What

### Happy Path

1. 실행자가 Railway API 주소를 지정한다.
2. 실행자가 각 음성파일과 기대 라벨을 `FILE_PATH=LABEL` 형식으로 지정한다.
3. 평가기가 `/api/analyze`에 업로드한다.
4. `queued`부터 `completed`까지 상태를 polling한다.
5. 결과를 수집하고 전체 지표를 출력한다.

### Edge Case

- 존재하지 않는 파일은 실행 전에 거부한다.
- 지원하지 않는 기대 라벨은 실행 전에 거부한다.
- 분석 상태가 `failed`이면 해당 작업의 상태와 함께 실패한다.
- 지정한 제한 시간 안에 완료되지 않으면 timeout으로 실패한다.
- 분모가 0인 지표는 0.0으로 반환한다.

## How

- `tools/evaluate_api.py`는 실행 시 입력만 받고 결과를 stdout에 출력한다.
- `tools/model_evaluation.py`는 API와 독립적으로 confusion matrix 기반 지표를 계산한다.
- API 요청은 기존 `audio` multipart field와 `/api/analyze` 계약을 사용한다.
- 기대 라벨은 `--case "C:\\path\\sample.wav=normal"`처럼 사용자가 직접 입력한다.
- 기본 polling 간격은 2초, 작업 제한 시간은 600초다.

## AC

- **Given** 네 개의 파일 경로와 기대 라벨을 명시적으로 입력하면 **When** 평가기를 실행할 때 **Then** 파일명과 무관하게 기대 라벨을 평가에 사용한다.
- **Given** API 작업이 실행 중이면 **When** 상태를 polling할 때 **Then** `stage`와 `progress`를 출력한다.
- **Given** 네 가지 confusion matrix 경우가 있으면 **When** 지표를 계산할 때 **Then** TP·TN·FP·FN과 Accuracy·Precision·Recall·F1·FPR을 반환한다.
- **Given** 존재하지 않는 파일 또는 잘못된 라벨이면 **When** 실행 인자를 파싱할 때 **Then** 명확한 입력 오류로 중단한다.
- **Given** API 작업이 실패하면 **When** 상태를 확인할 때 **Then** 성공 결과를 생성하지 않고 실패 정보를 포함해 중단한다.
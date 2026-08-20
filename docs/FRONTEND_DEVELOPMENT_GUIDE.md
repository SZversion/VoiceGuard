# 보이스피싱 통화 분석 MVP 프론트엔드 개발 가이드

이 문서는 팀 프로젝트의 프론트엔드를 먼저 개발한 뒤, 백엔드 FastAPI Endpoint가 준비되면 최소한의 설정 변경으로 연결·배포하기 위한 실행 순서 가이드입니다.

## 1. 최종 확정 기준

### 1.1 담당 범위

- 개인 통합 브랜치: YYH01/feature/project-mine
- 실제 프론트엔드 작업 브랜치: YYH01/feature/frontend
- 담당 영역: Nuxt 3 프론트엔드
- 프론트엔드 배포: Netlify
- 백엔드 배포: Railway의 FastAPI 서버
- 개발 방식: Mock API로 선개발 후 실제 API로 교체
- 병합 순서: YYH01/feature/frontend → YYH01/feature/project-mine → main

### 1.2 MVP 화면

~~~text
pages/
├─ index.vue       # 통화 파일 업로드
├─ analyze.vue     # 분석 진행 상태
├─ result.vue      # 분석 결과
├─ privacy.vue     # 개인정보 보호 안내
└─ help.vue        # 사용법 및 FAQ
~~~

### 1.3 페이지별 주요 기능

#### 1.3.1 업로드 페이지: `pages/index.vue`

주요 기능:

- 개인정보 처리 안내 및 동의
- 모델 준비 상태 확인
- 모델 준비 전 업로드 비활성화
- WAV·MP3·M4A 파일 선택
- 파일 형식·크기 검증
- 파일명·파일 크기 표시
- 분석 시작
- `POST /analyze` 호출
- 반환된 `job_id` 저장
- 분석 진행 페이지 이동

추천 컴포넌트:

~~~text
components/ConsentNotice.vue
components/ModelStatus.vue
components/AudioUploader.vue
components/FileInfo.vue
~~~

추천 커밋:

~~~text
feat: add upload page
feat: add audio file validation
feat: add model readiness check
~~~

#### 1.3.2 분석 진행 페이지: `pages/analyze.vue`

주요 기능:

- 업로드 파일 정보 표시
- 분석 진행률 표시
- 현재 분석 단계 표시
- 예상 완료 시간 표시
- 단계별 완료·진행 중·대기 상태 표시
- 분석 취소
- 분석 실패 안내
- 다시 분석하기
- 분석 완료 후 결과 페이지 이동

상태값:

~~~text
queued
preprocessing
transcribing
classifying
finalizing
completed
failed
cancelled
~~~

추천 컴포넌트:

~~~text
components/AnalysisProgress.vue
components/AnalysisSteps.vue
components/AnalysisFileInfo.vue
components/AnalysisError.vue
~~~

추천 커밋:

~~~text
feat: add analysis progress page
feat: add analysis status polling
feat: add analysis cancel flow
fix: handle analysis failure state
~~~

#### 1.3.3 결과 페이지: `pages/result.vue`

주요 기능:

- `/analyze/{job_id}/result` 호출
- 정상 통화·보이스피싱 의심 표시
- 점수 퍼센트 표시
- 위험도 5단계 표시
- 위험도 요약 카드 표시
- 최대 3개 위험 구간 표시
- 위험 구간 시간·내용·판단 근거 표시
- 대응 안내 표시
- 법적 확정 판정이 아니라는 문구 표시
- 다시 업로드하기
- 112·1332 안내

MVP에서 전체 전사문, 위험 구간 음성 재생, TTS 안내 음성은 구현하지 않습니다.

추천 컴포넌트:

~~~text
components/RiskSummaryCard.vue
components/RiskSegmentList.vue
components/AdviceCard.vue
components/DisclaimerNotice.vue
components/ReportContactCard.vue
~~~

추천 커밋:

~~~text
feat: add result page
feat: add risk summary card
feat: add risk segment list
feat: add response guidance
~~~

#### 1.3.4 개인정보 보호 안내 페이지: `pages/privacy.vue`

주요 기능:

- 음성파일 임시 처리 안내
- 분석 완료·실패·취소 후 삭제 안내
- 분석 이력 미저장 안내
- 외부 저장소 미사용 안내
- 제3자 서비스에 영구 저장하지 않는다는 안내
- AI 분석 결과의 법적 한계 안내

권장 안내 문구:

~~~text
업로드한 파일은 자체 분석 서버에서 분석 목적으로 임시 처리되며,
분석 완료 또는 오류 발생 후 삭제됩니다.
제3자 저장소에 영구 저장하지 않습니다.
~~~

추천 커밋:

~~~text
feat: add privacy information page
~~~

#### 1.3.5 도움말 페이지: `pages/help.vue`

주요 기능:

- 서비스 사용 방법
- 음성파일 업로드 방법
- 분석 진행 상태 설명
- 위험도 읽는 방법
- 위험 구간 의미 설명
- 분석 결과의 한계 안내
- 지원 파일 형식 FAQ
- 파일 보관 여부 FAQ
- 분석 소요 시간 FAQ
- 112·1332 연락 안내
- 업로드 페이지 이동

추천 컴포넌트:

~~~text
components/HowToUse.vue
components/ResultGuide.vue
components/FaqAccordion.vue
components/EmergencyContact.vue
~~~

추천 커밋:

~~~text
feat: add help page
feat: add faq accordion
feat: add emergency contact links
~~~

### 1.4 MVP에서 제외하는 기능

- 전체 전사문 탭
- 위험 구간 음성 재생
- TTS 안내 음성
- 분석 이력 저장
- 모바일 앱 및 실시간 통화 분석
- 자동 신고 및 보호자 연락
- 결과 파일 다운로드

위 기능은 디자인이나 문서에 존재하더라도 이번 프론트엔드 구현 범위에 추가하지 않습니다.

## 2. 최종 백엔드 Endpoint 계약

백엔드 담당자는 아래 경로를 기준으로 구현해야 합니다. /api/v1 prefix는 사용하지 않습니다.

| Method | Path | 역할 |
|---|---|---|
| GET | /health | API 서버 상태 확인 |
| GET | /model-status | STT·분류 모델 준비 상태 확인 |
| POST | /analyze | 음성파일 분석 작업 생성 및 job_id 반환 |
| GET | /analyze/{job_id}/status | 분석 작업 상태 조회 |
| GET | /analyze/{job_id}/result | 분석 완료 결과 조회 |
| DELETE | /analyze/{job_id} | 분석 취소 및 결과 폐기 |

### 2.1 분석 요청

~~~http
POST /analyze
Content-Type: multipart/form-data
~~~

파일 필드명은 audio로 통일합니다.

~~~json
{
  "job_id": "job_12345",
  "status": "queued",
  "stage": "queued"
}
~~~

### 2.2 상태 조회 응답

~~~json
{
  "job_id": "job_12345",
  "status": "running",
  "progress": 60,
  "stage": "classifying",
  "stage_label": "위험도 분류",
  "estimated_seconds": 50
}
~~~

상태값은 다음 중 하나로 통일합니다.

~~~text
queued
preprocessing
transcribing
classifying
finalizing
completed
failed
cancelled
~~~

### 2.3 결과 조회 응답

~~~json
{
  "job_id": "job_12345",
  "status": "completed",
  "label": "보이스피싱 의심",
  "score": 91.0,
  "risk_level": 5,
  "risk_level_label": "매우 높음",
  "summary": {
    "title": "보이스피싱 의심",
    "description": "기관 사칭과 금전 이체 유도 표현이 확인되었습니다."
  },
  "segments": [
    {
      "start_time": 84.0,
      "end_time": 96.0,
      "speaker": "other",
      "text": "저는 서울중앙지검 수사관입니다.",
      "reason": "수사기관 사칭 표현"
    }
  ],
  "advice": [
    "절대 돈을 이체하지 마세요.",
    "통화를 종료하세요.",
    "공식 기관 대표번호로 확인하세요."
  ],
  "disclaimer": "AI 분석 결과는 법적 확정 판정이 아닙니다."
}
~~~

segments는 최대 3개만 반환합니다. 화자 표시를 사용하려면 백엔드가 speaker 값을 제공해야 하며, 값이 없을 때 프론트가 임의로 화자를 추정하지 않습니다.

## 3. Git 브랜치 운영

작은 프로젝트이므로 개인 통합 브랜치와 실제 작업 브랜치를 분리해 사용합니다. 기능별 작업은 실제 작업 브랜치에서 진행하고, 작업이 끝나면 개인 통합 브랜치에 먼저 병합합니다.

~~~text
main
└─ YYH01/feature/project-mine       # 개인 프론트엔드 통합 브랜치
   └─ YYH01/feature/frontend        # 실제 프론트엔드 작업 브랜치
~~~

main과 YYH01/feature/project-mine에서 직접 기능 개발을 하지 않습니다. 실제 프론트엔드 개발은 YYH01/feature/frontend에서 진행합니다.

### 3.1 작업 시작

~~~bash
git fetch origin
git switch YYH01/feature/project-mine
git pull origin YYH01/feature/project-mine
git switch -c YYH01/feature/frontend
git push -u origin YYH01/feature/frontend
~~~

이미 YYH01/feature/frontend 브랜치가 있다면 새로 만들지 않고 다음처럼 이동합니다.

~~~bash
git fetch origin
git switch YYH01/feature/frontend
git pull origin YYH01/feature/frontend
~~~

실제 작업은 YYH01/feature/frontend에서 진행합니다.

### 3.2 커밋 단위

페이지 또는 기능 단위로 작게 커밋합니다.

~~~text
feat: add Nuxt project base setup
feat: add upload page
feat: add analysis progress page
feat: add result page
feat: add mock analysis api
feat: add error and cancel states
chore: configure Netlify environment variables
~~~

작업이 끝날 때마다 원격 브랜치에 Push합니다.

~~~bash
git add .
git commit -m "feat: add upload page"
git push origin YYH01/feature/frontend
~~~

작업 단위가 끝나면 GitHub에서 다음 방향으로 Pull Request를 생성합니다.

~~~text
YYH01/feature/frontend → YYH01/feature/project-mine
~~~

### 3.3 frontend에서 project-mine으로 병합하는 방법

작업이 완료되면 먼저 실제 작업 브랜치의 변경사항을 저장하고 원격 저장소에 Push합니다.

~~~bash
git switch YYH01/feature/frontend
git status
git add .
git commit -m "feat: complete frontend work"
git push origin YYH01/feature/frontend
~~~

그다음 GitHub에서 Pull Request를 생성합니다.

```text
Base repository: 팀 저장소
Base branch: YYH01/feature/project-mine
Compare branch: YYH01/feature/frontend
```

Pull Request 설명에는 다음 내용을 작성합니다.

- 구현한 화면과 기능
- Mock API 사용 여부
- 실제 백엔드 API 연결 여부
- 실행 방법
- 테스트한 명령어
- 알려진 제한사항

병합 전 다음 항목을 확인합니다.

- [ ] 업로드·분석 진행·결과 화면이 정상 동작한다.
- [ ] 성공·실패·취소 상태를 확인했다.
- [ ] `pnpm lint`가 통과한다.
- [ ] `pnpm build`가 통과한다.
- [ ] `.env`와 개인정보가 커밋에 포함되지 않았다.
- [ ] Netlify Preview에서 화면을 확인했다.

팀원 리뷰와 확인이 끝나면 GitHub의 `Merge pull request`를 사용하여 PR을 병합합니다.

```text
YYH01/feature/frontend → YYH01/feature/project-mine
```

PR 병합 후에는 로컬의 개인 통합 브랜치를 원격 상태와 동기화합니다.

~~~bash
git fetch origin
git switch YYH01/feature/project-mine
git pull origin YYH01/feature/project-mine
pnpm install
pnpm lint
pnpm build
~~~

병합 후 전체 프론트엔드 흐름을 다시 확인합니다.

- [ ] 업로드 화면
- [ ] 모델 상태 확인
- [ ] 분석 작업 생성
- [ ] 분석 상태 조회
- [ ] 분석 결과 조회
- [ ] 분석 취소
- [ ] 실패 및 재시도

문제가 없으면 다음 작업은 다시 `YYH01/feature/frontend`를 기준으로 진행합니다. 기존 브랜치를 계속 사용할 경우 먼저 최신 `project-mine`을 반영합니다.

~~~bash
git fetch origin
git switch YYH01/feature/frontend
git pull origin YYH01/feature/frontend
git merge origin/YYH01/feature/project-mine
~~~

작업 브랜치를 새로 만들고 싶다면 최신 `project-mine`에서 새 작업 브랜치를 생성합니다.

~~~bash
git switch YYH01/feature/project-mine
git pull origin YYH01/feature/project-mine
git switch -c YYH01/feature/frontend-next
git push -u origin YYH01/feature/frontend-next
~~~

## 4. 프론트엔드 프로젝트 구성

권장 구조는 다음과 같습니다.

~~~text
frontend/
├─ pages/
├─ components/
├─ composables/
│  └─ useAnalysisApi.ts
├─ types/
│  └─ analysis.ts
├─ mocks/
│  └─ analysisMock.ts
├─ utils/
├─ public/
├─ .env.example
├─ nuxt.config.ts
└─ package.json
~~~

페이지 컴포넌트에서 직접 fetch하지 않고 useAnalysisApi.ts를 통해 호출합니다.

~~~text
페이지
  ↓
useAnalysisApi()
  ↓
Mock API 또는 실제 FastAPI API
~~~

이 구조를 사용하면 백엔드가 완성된 후 화면 컴포넌트를 다시 수정하지 않고 API 연결부와 환경변수만 교체할 수 있습니다.

## 5. Mock API로 먼저 개발하기

### 5.1 로컬 환경변수

.env 파일은 GitHub에 올리지 않습니다.

~~~env
NUXT_PUBLIC_USE_MOCK=true
NUXT_PUBLIC_API_BASE=http://localhost:8000
~~~

.env.example에는 실제 비밀값 없이 기본 구조만 기록합니다.

~~~env
NUXT_PUBLIC_USE_MOCK=true
NUXT_PUBLIC_API_BASE=http://localhost:8000
~~~

### 5.2 Mock으로 확인할 상태

프론트에서는 다음 상태를 모두 재현할 수 있어야 합니다.

~~~text
queued
preprocessing
transcribing
classifying
finalizing
completed
failed
cancelled
~~~

최소한 다음 화면을 먼저 완성합니다.

1. 파일 선택
2. 파일 확장자 및 크기 검증
3. 분석 시작
4. 분석 진행 상태 표시
5. 분석 취소
6. 완료 결과 표시
7. 실패 오류 표시
8. 다시 분석하기

## 6. 프론트엔드 API 호출 규칙

### 6.1 API Base URL

nuxt.config.ts에서 환경변수를 사용합니다.

~~~ts
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      useMock: process.env.NUXT_PUBLIC_USE_MOCK === 'true'
    }
  }
})
~~~

### 6.2 호출 순서

~~~text
GET /model-status
  ↓ ready 확인
POST /analyze
  ↓ job_id 저장
GET /analyze/{job_id}/status 반복 호출
  ↓ completed 확인
GET /analyze/{job_id}/result
  ↓ 결과 화면 표시
~~~

취소 버튼을 누르면 다음 API를 호출합니다.

~~~http
DELETE /analyze/{job_id}
~~~

상태 조회는 completed, failed, cancelled 중 하나가 될 때 중단합니다.

## 7. 백엔드 Endpoint가 완성된 뒤 실제 API로 교체하기

### 7.1 백엔드 담당자에게 받을 정보

- Railway FastAPI 공개 URL
- Swagger 주소: /docs
- API 경로와 HTTP Method
- 업로드 필드명: audio
- 지원 파일 형식
- 최대 파일 크기
- 상태값 목록
- 결과 JSON 예시
- 오류 응답 형식
- CORS 허용 완료 여부

### 7.2 환경변수만 변경

로컬에서 실제 백엔드를 테스트할 때:

~~~env
NUXT_PUBLIC_USE_MOCK=false
NUXT_PUBLIC_API_BASE=https://backend-test.up.railway.app
~~~

Netlify 운영 환경에서는 Netlify의 환경변수 설정 화면에 다음을 등록합니다.

~~~env
NUXT_PUBLIC_USE_MOCK=false
NUXT_PUBLIC_API_BASE=https://backend-production.up.railway.app
~~~

환경변수에 실제 API 키나 비밀번호를 넣지 않습니다. 프론트 공개 환경변수에는 공개 API 주소만 넣습니다.

### 7.3 응답 변환 계층

백엔드 응답과 화면에서 사용하는 타입이 다를 수 있으므로 normalizeAnalysisResult() 같은 변환 함수를 둡니다.

~~~text
FastAPI 응답
  ↓
응답 변환 함수
  ↓
프론트엔드 공통 타입
  ↓
결과 화면
~~~

이렇게 하면 백엔드 필드가 일부 변경되어도 여러 화면을 동시에 수정하지 않아도 됩니다.

## 8. CORS 설정

FastAPI 담당자는 다음 출처를 허용해야 합니다.

~~~text
http://localhost:3000
https://deploy-preview-번호--사이트명.netlify.app
https://사이트명.netlify.app
~~~

프론트가 호출하는 주소와 백엔드가 허용하는 주소가 다르면 브라우저에서 CORS 오류가 발생합니다.

CORS는 백엔드 담당자가 설정하며, 프론트에서 우회하지 않습니다. Preview URL이 매번 달라지는 경우 Netlify 사이트 도메인 정책을 팀에서 정하고 백엔드 허용 목록에 반영합니다.

## 9. Netlify 배포

### 9.1 Preview 배포

1. GitHub 저장소를 Netlify에 연결합니다.
2. 작업 브랜치 또는 Pull Request를 Preview 대상으로 설정합니다.
3. Build command를 프로젝트에 맞게 설정합니다.

~~~text
Build command: pnpm build
Publish directory: Nuxt 설정에 맞는 출력 경로
~~~

Nuxt SSR 배포 방식을 사용할 경우 Netlify의 Nuxt 지원 방식과 프로젝트의 package.json 스크립트를 확인합니다. 정적 배포를 선택할 경우 SSR·서버 API 사용 여부를 먼저 확인합니다.

### 9.2 Netlify 환경변수

Preview:

~~~env
NUXT_PUBLIC_USE_MOCK=true
NUXT_PUBLIC_API_BASE=http://localhost:8000
~~~

실제 백엔드 통합 Preview:

~~~env
NUXT_PUBLIC_USE_MOCK=false
NUXT_PUBLIC_API_BASE=https://backend-test.up.railway.app
~~~

Production:

~~~env
NUXT_PUBLIC_USE_MOCK=false
NUXT_PUBLIC_API_BASE=https://backend-production.up.railway.app
~~~

### 9.3 Netlify 배포 확인

- 새로고침 후 페이지가 정상 표시되는지 확인
- 환경변수가 실제 빌드에 반영되었는지 확인
- 브라우저 Network 탭에서 API 주소 확인
- CORS 오류 확인
- 업로드·진행·결과·취소 흐름 확인

## 10. Railway FastAPI 연결 테스트

백엔드가 Railway에 배포되면 먼저 브라우저나 Swagger에서 다음을 확인합니다.

~~~text
GET https://backend-test.up.railway.app/health
GET https://backend-test.up.railway.app/model-status
~~~

확인 순서:

1. /health 응답 확인
2. /model-status가 ready인지 확인
3. Swagger에서 /analyze 파일 업로드 확인
4. job_id 반환 확인
5. /status 응답 확인
6. /result 응답 확인
7. DELETE 취소 확인
8. Railway 로그에서 개인정보가 출력되지 않는지 확인

## 11. 구현 전 체크리스트

- [ ] 최신 main을 작업 브랜치에 반영했다.
- [ ] YYH01/feature/frontend에서 작업 중이다.
- [ ] .env가 Git에 포함되지 않는다.
- [ ] Mock API와 실제 API 전환 구조가 있다.
- [ ] 업로드 필드명이 audio로 고정되었다.
- [ ] API 경로에 /api/v1를 사용하지 않는다.
- [ ] 상태 API와 결과 API를 분리했다.
- [ ] 분석 취소 상태를 처리한다.
- [ ] 실패·재시도 화면을 처리한다.
- [ ] 모델 준비 전 업로드를 제한한다.
- [ ] 지원하지 않는 파일을 차단한다.
- [ ] 최대 파일 크기를 프론트와 백엔드에서 동일하게 적용한다.

## 12. 실제 API 연결 체크리스트

- [ ] Railway FastAPI 공개 URL을 받았다.
- [ ] /health가 정상 응답한다.
- [ ] /model-status가 정상 응답한다.
- [ ] POST /analyze가 job_id를 반환한다.
- [ ] 상태 조회가 단계별로 동작한다.
- [ ] 결과 조회가 완료 후 동작한다.
- [ ] 취소 API가 동작한다.
- [ ] CORS에 localhost 주소가 등록되어 있다.
- [ ] CORS에 Netlify Preview 주소가 등록되어 있다.
- [ ] CORS에 Netlify 운영 주소가 등록되어 있다.
- [ ] 실제 결과 JSON이 프론트 타입과 일치한다.
- [ ] Railway에서 원본·임시 데이터 삭제가 확인된다.

## 13. main 병합 전 작업

YYH01/feature/frontend의 기능이 모두 YYH01/feature/project-mine에 병합되면, 개인 통합 브랜치에 최신 main을 반영합니다.

- [ ] YYH01/feature/frontend의 작업을 YYH01/feature/project-mine에 병합했다.
- [ ] project-mine에서 전체 프론트엔드 흐름을 다시 테스트했다.

~~~bash
git fetch origin
git switch YYH01/feature/project-mine
git pull origin YYH01/feature/project-mine
git merge origin/main
~~~

충돌을 해결한 후 검증합니다.

~~~bash
pnpm install
pnpm lint
pnpm build
~~~

검증이 끝나면 Push합니다.

~~~bash
git add .
git commit -m "chore: prepare frontend integration"
git push origin YYH01/feature/project-mine
~~~

그다음 GitHub에서 최종 Pull Request를 생성합니다.

~~~text
YYH01/feature/project-mine → main
~~~

main에 직접 Push하지 않습니다. 팀 리뷰와 CI 확인 후 PR을 병합합니다.

## 14. 최종 완료 기준

다음 조건을 모두 확인하면 프론트엔드 작업 완료로 판단합니다.

- 업로드 화면이 디자인과 일치한다.
- 모델 준비 상태를 확인할 수 있다.
- Mock API로 전체 흐름이 동작한다.
- 실제 Railway API로 업로드와 결과 조회가 동작한다.
- 분석 상태와 결과 API가 분리되어 있다.
- 취소·실패·재시도 상태가 동작한다.
- Netlify Preview에서 브라우저 오류가 없다.
- CORS 오류가 없다.
- pnpm lint가 통과한다.
- pnpm build가 통과한다.
- 개인정보와 음성 원문이 프론트 로그에 출력되지 않는다.
- GitHub PR 설명에 테스트 방법과 환경변수를 기록했다.
- main 병합 후 Netlify Production에서 최종 화면을 확인했다.

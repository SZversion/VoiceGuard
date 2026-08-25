# 보이스피싱 통화 분석 MVP 프론트엔드

음성 파일 업로드부터 분석 진행 상태와 분석 결과 확인까지의 사용자 화면을 담당하는 Nuxt 프론트엔드입니다.

## 주요 기능

- 통화 녹음 파일 업로드
- 분석 진행 상태 확인
- 분석 결과와 대응 방법 표시
- 개인정보 보호 안내
- 사용 방법과 자주 묻는 질문 제공
- 모바일·태블릿·데스크톱 반응형 화면 지원

## 기술 스택

- Nuxt 3
- Vue 3
- Tailwind CSS
- Pinia
- Heroicons

## 폴더 구조

```text
frontend/
├─ assets/       # 전역 스타일
├─ components/   # 공통 UI 컴포넌트
├─ composables/  # API 호출 등 재사용 로직
├─ layouts/      # 기본 화면 레이아웃과 네비게이션
├─ mocks/        # 로컬 Mock API 데이터
├─ pages/        # Nuxt 페이지 라우트
├─ public/       # 정적 이미지·아이콘
├─ types/        # 분석 데이터 타입
├─ app.vue
├─ nuxt.config.mjs
└─ package.json
```

## 로컬 실행

명령어는 이 `frontend` 폴더에서 실행합니다.

```bash
pnpm install
pnpm dev
```

개발 서버 기본 주소:

```text
http://localhost:3000
```

## 환경 변수

`frontend/.env` 파일에 다음 값을 설정할 수 있습니다.

```env
NUXT_PUBLIC_USE_MOCK=false
NUXT_PUBLIC_API_BASE=http://localhost:8000
```

- `NUXT_PUBLIC_USE_MOCK=true`: 로컬 Mock API 사용
- `NUXT_PUBLIC_USE_MOCK=false`: FastAPI 백엔드 API 사용
- `NUXT_PUBLIC_API_BASE`: 연결할 백엔드 주소

실제 배포 환경에서는 `localhost` 대신 배포된 FastAPI 백엔드 주소를 사용해야 합니다.

## 빌드 확인

```bash
pnpm build
pnpm preview
```

`pnpm build`가 성공한 뒤 `pnpm preview`로 production 빌드 결과를 확인할 수 있습니다.

## Netlify 배포

현재 저장소는 다음과 같이 설정합니다.

```text
Repository: aihuman-7th/proj1-e
Base directory: frontend
Build command: pnpm build
Publish directory: frontend/dist
Production branch: main
Test branch: YYH01/feature/frontend
```

`YYH01/feature/frontend`는 Branch Deploy 또는 PR Deploy Preview로 먼저 확인합니다. 테스트가 완료되면 GitHub PR을 `main`에 병합하고, `main`의 Production Deploy 결과를 확인합니다.

## 작업 원칙

- API 키와 비밀번호를 저장소에 커밋하지 않습니다.
- 배포 환경에서는 실제 백엔드 주소와 환경별 환경 변수를 사용합니다.
- UI 변경 후 모바일, 태블릿, 데스크톱 화면을 각각 확인합니다.
- 변경 전후 `git diff --check`와 production build를 확인합니다.

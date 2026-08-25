# Nuxt 3 PWA 설정 가이드

## 목차
1. [개요](#개요)
2. [패키지 설치](#패키지-설치)
3. [아이콘 준비 및 자동 생성](#아이콘-준비-및-자동-생성)
4. [nuxt.config.ts 설정](#nuxtconfigts-설정)
5. [app.vue 설정](#appvue-설정)
6. [Web App Manifest](#web-app-manifest)
7. [Service Worker](#service-worker)
8. [오프라인 페이지](#오프라인-페이지)
9. [푸시 알림 (선택)](#푸시-알림-선택)
10. [배포 전 체크리스트](#배포-전-체크리스트)
11. [자주 발생하는 문제](#자주-발생하는-문제)
12. [모듈 사용 시 자동 생성 파일 정리](#모듈-사용-시-자동-생성-파일-정리)
13. [배포 흐름 요약](#배포-흐름-요약)

---

## 개요

Nuxt 3에서 PWA를 구현하는 가장 권장되는 방법은 **`@vite-pwa/nuxt`** 모듈을 사용하는 것입니다.  
이 모듈은 [vite-plugin-pwa](https://vite-pwa-org.netlify.app/)를 기반으로 하며, Service Worker 자동 생성, Manifest 설정, 캐싱 전략 등을 손쉽게 구성할 수 있습니다.

### 표준 설정 원칙

- 아이콘은 `public/images/icons/` 폴더에 관리
- `icon-512.png` 하나만 준비하면 나머지는 CLI로 자동 생성
- `nuxt build` 시 `sw.js`, `manifest.webmanifest`는 자동 생성 (직접 만들지 않음)
- 개발 중 Service Worker 비활성화 (캐시 문제 방지), 빌드 후 `preview`로 확인

---

## 패키지 설치

```bash
# PWA 모듈 + 아이콘 생성 CLI
npm install -D @vite-pwa/nuxt @vite-pwa/assets-generator
```

---

## 아이콘 준비 및 자동 생성

### 1단계: 소스 아이콘 배치

`icon-512.png` 파일 하나만 준비해서 아래 경로에 배치합니다.

```
public/
└── images/
    └── icons/
        └── icon-512.png   ← 이 파일 하나만 직접 준비
```

### 2단계: package.json에 스크립트 추가

```json
{
  "scripts": {
    "build": "nuxt build",
    "dev": "nuxt dev",
    "generate": "nuxt generate",
    "preview": "nuxt preview",
    "postinstall": "nuxt prepare",
    "generate-icons": "pwa-assets-generator --preset minimal-2023 public/images/icons/icon-512.png"
  }
}
```

### 3단계: 아이콘 생성 실행

```bash
npm run generate-icons
```

실행 결과로 `public/images/icons/` 안에 다음 파일들이 자동 생성됩니다:

```
public/
└── images/
    └── icons/
        ├── icon-512.png               ← 직접 준비한 소스 이미지
        ├── pwa-64x64.png              ✅ 자동 생성 (Windows Edge)
        ├── pwa-192x192.png            ✅ 자동 생성 (PWA 필수)
        ├── pwa-512x512.png            ✅ 자동 생성 (PWA 필수)
        ├── maskable-icon-512x512.png  ✅ 자동 생성 (Android 어댑티브)
        ├── apple-touch-icon-180x180.png ✅ 자동 생성 (iOS/macOS)
        └── favicon.ico                ✅ 자동 생성 (브라우저 탭)
```

> 💡 **새 프로젝트마다**: `icon-512.png`만 교체하고 `npm run generate-icons`를 한 번 실행하면 됩니다.

> ⚠️ **favicon.ico 위치**: 생성된 favicon.ico는 `public/images/icons/`에 생성됩니다.  
> `nuxt.config.ts`의 `link` 태그에 경로를 명시하면 루트 이동 없이 사용 가능합니다.

---

## nuxt.config.ts 설정

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  modules: [
    '@vite-pwa/nuxt',
  ],

  app: {
    head: {
      meta: [
        { name: 'theme-color', content: '#ffffff' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
        { name: 'apple-mobile-web-app-title', content: '앱 이름' },
      ],
      link: [
        { rel: 'icon', href: '/images/icons/favicon.ico', sizes: '48x48' },
        { rel: 'apple-touch-icon', href: '/images/icons/apple-touch-icon-180x180.png' },
      ],
    },
  },

  pwa: {
    /* ─── 기본 정보 ─── */
    registerType: 'autoUpdate', // 포트폴리오·정보성 사이트: 'autoUpdate' / 서비스 앱: 'prompt'
    injectRegister: 'auto',

    /* ─── Manifest ─── */
    manifest: {
      name: '앱 이름',
      short_name: '짧은 이름',
      description: '앱 설명',
      theme_color: '#ffffff',
      background_color: '#ffffff',
      display: 'standalone',       // 'standalone' | 'fullscreen' | 'minimal-ui'
      orientation: 'portrait',
      scope: '/',
      start_url: '/',
      icons: [
        { src: '/images/icons/pwa-64x64.png', sizes: '64x64', type: 'image/png' },
        { src: '/images/icons/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/images/icons/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: '/images/icons/maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },

    /* ─── Workbox (캐싱 전략) ─── */
    workbox: {
      globPatterns: ['**/*.{js,css,html,png,svg,ico,woff,woff2}'],
      navigateFallback: null,   // ⚠️ 필수: non-precached-url 에러 방지
      skipWaiting: true,        // 새 SW 즉시 활성화
      clientsClaim: true,       // 기존 탭도 새 SW로 즉시 전환
      runtimeCaching: [
        {
          // 이미지: 캐시 우선 (30일 보관)
          urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
          handler: 'CacheFirst',
          options: {
            cacheName: 'image-cache',
            expiration: {
              maxEntries: 60,
              maxAgeSeconds: 60 * 60 * 24 * 30,
            },
            cacheableResponse: {
              statuses: [0, 200],
            },
          },
        },
        {
          // 폰트: 캐시 우선 (1년 보관)
          urlPattern: /\.(?:woff|woff2|ttf|eot)$/i,
          handler: 'CacheFirst',
          options: {
            cacheName: 'font-cache',
            expiration: {
              maxEntries: 30,
              maxAgeSeconds: 60 * 60 * 24 * 365,
            },
            cacheableResponse: {
              statuses: [0, 200],
            },
          },
        },
        // API 요청이 있는 앱의 경우 아래 추가
        // {
        //   urlPattern: /^https?:\/\/.*\/api\/.*/i,
        //   handler: 'NetworkFirst',
        //   options: {
        //     cacheName: 'api-cache',
        //     expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 },
        //     cacheableResponse: { statuses: [0, 200] },
        //   },
        // },
      ],
    },

    /* ─── 개발 환경 설정 ─── */
    devOptions: {
      enabled: false,   // ✅ 개발 시 SW 비활성화 (캐시 문제 방지)
      suppressWarnings: true,
      type: 'module',
    },
  },
})
```

---

## app.vue 설정

`VitePwaManifest` 컴포넌트를 추가해 manifest 링크가 HTML에 주입되도록 합니다.

```vue
<!-- app.vue -->
<template>
  <div>
    <VitePwaManifest />
    <NuxtPage />
  </div>
</template>
```

> ℹ️ `registerType: 'prompt'` 사용 시 업데이트 알림 컴포넌트를 추가할 수 있습니다.  
> 자세한 내용은 [SW 업데이트 알림 컴포넌트](#sw-업데이트-알림-컴포넌트) 참고.

---

## Web App Manifest

### display 옵션 비교

| 값 | 설명 |
|---|---|
| `standalone` | 네이티브 앱처럼 보임 (가장 일반적) |
| `fullscreen` | 상태바 포함 전체 화면 |
| `minimal-ui` | 최소한의 브라우저 UI 표시 |
| `browser` | 일반 브라우저와 동일 |

### registerType 선택 기준

| 값 | 설명 | 권장 용도 |
|---|---|---|
| `autoUpdate` | 새 버전 감지 시 자동 업데이트 | 포트폴리오, 정보성 사이트 |
| `prompt` | 업데이트 시 사용자에게 알림 | 서비스 앱, 데이터 손실 우려 시 |

---

## Service Worker

### 캐싱 전략 종류

| 전략 | 설명 | 적합한 용도 |
|---|---|---|
| `CacheFirst` | 캐시 우선, 없으면 네트워크 | 이미지, 폰트 등 정적 리소스 |
| `NetworkFirst` | 네트워크 우선, 실패 시 캐시 | API, 자주 바뀌는 데이터 |
| `StaleWhileRevalidate` | 캐시 반환 후 백그라운드 갱신 | HTML, JS, CSS |
| `NetworkOnly` | 항상 네트워크만 사용 | 결제, 인증 등 중요 요청 |
| `CacheOnly` | 항상 캐시만 사용 | 완전 오프라인 앱 |

### SW 업데이트 알림 컴포넌트

`registerType: 'prompt'` 사용 시, 사용자에게 업데이트를 안내할 수 있습니다.

```vue
<!-- components/PwaUpdatePrompt.client.vue -->
<template>
  <div v-if="pwa?.needRefresh" class="pwa-update-banner">
    <span>새로운 버전이 있습니다!</span>
    <button type="button" @click="updateSW()">업데이트</button>
    <button type="button" @click="close()">닫기</button>
  </div>
</template>

<script setup>
const pwa = usePWA()

const close = () => {
  pwa?.cancelPrompt()
}

const updateSW = async () => {
  await pwa?.updateServiceWorker(true)
}
</script>

<style scoped>
.pwa-update-banner {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: #333;
  color: #fff;
  padding: 1rem;
  border-radius: 8px;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  z-index: 9999;
}
</style>
```

> ⚠️ SSR 환경에서 `useRegisterSW` 오류를 방지하려면 파일명을 `.client.vue`로 만들고  
> `app.vue`에서 `<ClientOnly><PwaUpdatePrompt /></ClientOnly>`로 감싸서 사용합니다.

---

## 오프라인 페이지

`navigateFallback: null` 설정 시 오프라인 페이지 없이도 에러 없이 동작합니다.  
오프라인 페이지가 필요한 경우에만 아래를 추가하고 `navigateFallback: '/offline'`으로 변경합니다.

```vue
<!-- pages/offline.vue -->
<template>
  <div class="offline-page">
    <h1>오프라인 상태입니다</h1>
    <p>인터넷 연결을 확인해 주세요.</p>
    <button @click="retry">다시 시도</button>
  </div>
</template>

<script setup lang="ts">
const retry = () => {
  window.location.reload()
}
</script>
```

---

## 푸시 알림 (선택)

> HTTPS 환경에서만 동작합니다.

```ts
// composables/usePushNotification.ts
export const usePushNotification = () => {
  const subscribe = async () => {
    if (!('Notification' in window)) {
      console.warn('이 브라우저는 알림을 지원하지 않습니다.')
      return
    }

    const permission = await Notification.requestPermission()
    if (permission !== 'granted') return

    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: 'YOUR_VAPID_PUBLIC_KEY', // VAPID 키
    })

    // 서버에 subscription 전송
    await $fetch('/api/push/subscribe', {
      method: 'POST',
      body: subscription,
    })
  }

  return { subscribe }
}
```

---

## 배포 전 체크리스트

```
✅ icon-512.png 준비 후 npm run generate-icons 실행
✅ pwa-192x192.png, pwa-512x512.png 생성 확인
✅ maskable-icon-512x512.png 생성 확인 (Android)
✅ apple-touch-icon-180x180.png 생성 확인 (iOS)
✅ nuxt.config.ts manifest.icons 경로 일치 확인
✅ VitePwaManifest 컴포넌트 app.vue에 포함 확인
✅ HTTPS 환경에서 배포 (localhost 제외)
✅ npm run build → npm run preview 로 PWA 설치 버튼 동작 확인
✅ Chrome DevTools > Application > Service Workers 탭에서 SW 등록 확인
✅ Chrome DevTools > Application > Manifest 탭에서 manifest 확인
✅ Lighthouse PWA 점수 확인 (목표: 100점)
```

> ⚠️ **PWA 설치 버튼(홈 화면 추가)**은 `devOptions.enabled: false` 상태에서는 개발 서버에서 표시되지 않습니다.  
> 반드시 `npm run build && npm run preview` 또는 배포 환경에서 확인하세요.

### Lighthouse로 PWA 점수 확인

```bash
# Chrome DevTools > Lighthouse > PWA 항목 체크 후 분석 실행
# 또는 CLI
npx lighthouse https://your-domain.com --view
```

---

## 자주 발생하는 문제

### 1. 개발 서버에서 PWA 설치 버튼이 안 보임
```
원인: devOptions.enabled: false 설정
해결: npm run build && npm run preview 로 확인
     (개발 중 확인이 꼭 필요하면 devOptions.enabled: true 임시 변경)
```

### 2. `non-precached-url` 에러 발생
```ts
// nuxt.config.ts
workbox: {
  navigateFallback: null,  // ✅ 이 값으로 해결
}
```

### 3. 캐시가 갱신되지 않음 (업데이트가 반영 안 됨)
```ts
workbox: {
  skipWaiting: true,    // ✅ 새 SW 즉시 활성화
  clientsClaim: true,   // ✅ 기존 탭도 새 SW로 전환
}
```

### 4. iOS Safari에서 설치가 안 됨
iOS Safari는 `standalone` 모드만 지원하며, 메타 태그가 필수입니다.
```ts
// nuxt.config.ts app.head.meta
{ name: 'apple-mobile-web-app-capable', content: 'yes' },
{ name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
// app.head.link
{ rel: 'apple-touch-icon', href: '/images/icons/apple-touch-icon-180x180.png' },
```

### 5. `useRegisterSW is not defined` / `mounted$` 경고 (개발 서버)

원인은 `.client.vue` 부족만이 아닙니다. `devOptions.enabled: false`일 때 `useRegisterSW` 가상 모듈이 개발 서버에 없어서 500이 납니다.

Nuxt에서는 `useRegisterSW()`를 직접 쓰지 말고 `@vite-pwa/nuxt`의 `usePWA()` / `$pwa`를 씁니다. 개발 모드에서 `$pwa`는 `undefined`일 수 있으므로 optional chaining을 사용합니다.

```vue
<script setup>
const pwa = usePWA()
</script>

<template>
  <div v-if="pwa?.needRefresh">
    <button type="button" @click="pwa.updateServiceWorker(true)">업데이트</button>
    <button type="button" @click="pwa.cancelPrompt()">닫기</button>
  </div>
</template>
```

컴포넌트는 계속 `.client.vue`로 두고 `app.vue`에서는 `<ClientOnly>`로 감쌉니다. 설치·SW 동작 확인은 `npm run build && npm run preview`에서 합니다.

### 6. API 요청이 캐싱되면 안 될 때
```ts
workbox: {
  runtimeCaching: [
    {
      urlPattern: /\/api\/auth\/.*/i,
      handler: 'NetworkOnly', // 인증 API는 캐시 제외
    },
  ],
}
```

### 7. Netlify 빌드 시 파일 크기 초과 에러
```
오류: "xxx.jpg is 2.xx MB, and won't be precached"
원인: Workbox 기본 precache 용량 제한 2 MiB 초과
해결 1: 해당 이미지를 2 MB 이하로 압축 (권장)
해결 2: workbox.maximumFileSizeToCacheInBytes: 5 * 1024 * 1024 추가
```

### 8. `Failed to resolve import "#app-manifest"` (개발 서버)

PWA `manifest.webmanifest`와 **다른 문제**입니다. Nuxt 내부 `#app-manifest`를 Vite가 콜드 스타트에서 해석하지 못해 납니다. `@vite-pwa/nuxt`를 제거하거나 PWA를 끄면 안 됩니다.

`npm install` 또는 `npm run build` 직후 `npm run dev`를 실행하면 자주 재현됩니다.

```bash
# 1순위: 캐시 정리 (nuxt.config는 아직 바꾸지 않음)
rm -rf .nuxt .output node_modules/.cache
npm run postinstall
npm run dev
```

오류가 한 번 찍힌 뒤 Nitro/Vite가 정상 기동하면 첫 실행 노이즈로 두고, 브라우저에서 페이지가 열리는지만 확인합니다.

페이지가 실제로 안 열릴 때만 아래 우회를 씁니다. **PWA 설치 기능은 꺼지지 않습니다.** 클라이언트 `routeRules`는 동작하지 않을 수 있습니다.

```js
experimental: {
  appManifest: false,
}
```

---

## 모듈 사용 시 자동 생성 파일 정리

`@vite-pwa/nuxt` 모듈을 사용하면 아래 파일들은 **직접 만들 필요가 없습니다.**  
`nuxt build` 실행 시 `.output/public/` 안에 자동으로 생성됩니다.

| 파일 | 직접 작업 필요? | 비고 |
|---|---|---|
| `sw.js` | ❌ 자동 생성 | 빌드 시 자동 생성 |
| `manifest.webmanifest` | ❌ 자동 생성 | `/public`에 직접 두면 버그 위험 |
| `workbox-xxxx.js` | ❌ 자동 생성 | Workbox 런타임 |
| 아이콘 이미지들 | ✅ `generate-icons`로 생성 | `public/images/icons/`에 배치 |
| `favicon.ico` (루트) | ✅ 선택 | `link` 태그 경로 명시 시 루트 불필요 |

> ⚠️ **아이콘 파일이 없으면** manifest는 생성되지만 Lighthouse PWA 점수가 낮게 나오거나 설치 자체가 안 될 수 있습니다.

---

## 배포 흐름 요약

```
1. icon-512.png 를 public/images/icons/ 에 배치
       ↓
2. npm run generate-icons 실행
   → pwa-192x192.png, pwa-512x512.png, maskable-icon-512x512.png,
     apple-touch-icon-180x180.png, favicon.ico 자동 생성
       ↓
3. nuxt.config.ts 설정 (manifest.icons 경로 확인)
       ↓
4. app.vue 에 <VitePwaManifest /> 추가
       ↓
5. nuxt build 실행
   → sw.js, manifest.webmanifest 자동 생성
       ↓
6. npm run preview 로 PWA 설치 버튼 동작 확인
       ↓
7. HTTPS 환경에 배포
   (Vercel, Netlify, AWS 등 일반 배포 환경은 기본 HTTPS 제공)
       ↓
8. Lighthouse로 PWA 점수 확인 (목표: 100점)
```

> ⚠️ **HTTPS는 필수입니다.** Service Worker는 HTTP 환경에서 동작하지 않습니다 (localhost 제외).

---

## 참고 링크

- [@vite-pwa/nuxt 공식 문서](https://vite-pwa-org.netlify.app/frameworks/nuxt)
- [@vite-pwa/assets-generator 문서](https://vite-pwa-org.netlify.app/assets-generator/)
- [Web App Manifest MDN](https://developer.mozilla.org/ko/docs/Web/Manifest)
- [Workbox 공식 문서](https://developer.chrome.com/docs/workbox)
- [PWA Checklist - web.dev](https://web.dev/pwa-checklist/)

export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: false },
  experimental: {
    appManifest: false
  },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vite-pwa/nuxt'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      useMock: process.env.NUXT_PUBLIC_USE_MOCK !== 'false'
    }
  },
  app: {
    head: {
      title: '보이스피싱 통화 분석 MVP',
      meta: [
        {
          name: 'description',
          content: '통화 녹음파일의 보이스피싱 의심 여부를 확인하는 서비스'
        },
        { name: 'theme-color', content: '#10245b' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
        { name: 'apple-mobile-web-app-title', content: 'Voice Guard' }
      ],
      link: [
        { rel: 'icon', href: '/images/icons/favicon.ico', sizes: '48x48' },
        { rel: 'apple-touch-icon', href: '/images/icons/apple-touch-icon-180x180.png' }
      ]
    }
  },
  pwa: {
    registerType: 'autoUpdate',
    injectRegister: 'auto',
    manifest: {
      name: 'Voice Guard',
      short_name: 'Voice Guard',
      description: '통화 녹음파일의 보이스피싱 의심 여부를 확인하는 서비스',
      theme_color: '#10245b',
      background_color: '#f8fafc',
      display: 'standalone',
      scope: '/',
      start_url: '/',
      icons: [
        { src: '/images/icons/pwa-64x64.png', sizes: '64x64', type: 'image/png' },
        { src: '/images/icons/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/images/icons/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: '/images/icons/maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
      ]
    },
    workbox: {
      globPatterns: ['**/*.{js,css,html,png,svg,gif,webp,ico,woff,woff2}'],
      navigateFallback: null,
      skipWaiting: true,
      clientsClaim: true,
      runtimeCaching: [
        {
          urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
          handler: 'CacheFirst',
          options: {
            cacheName: 'image-cache',
            expiration: {
              maxEntries: 60,
              maxAgeSeconds: 60 * 60 * 24 * 30
            },
            cacheableResponse: {
              statuses: [0, 200]
            }
          }
        },
        {
          urlPattern: /\.(?:woff|woff2|ttf|eot)$/i,
          handler: 'CacheFirst',
          options: {
            cacheName: 'font-cache',
            expiration: {
              maxEntries: 30,
              maxAgeSeconds: 60 * 60 * 24 * 365
            },
            cacheableResponse: {
              statuses: [0, 200]
            }
          }
        }
      ]
    },
    devOptions: {
      enabled: false,
      suppressWarnings: true,
      type: 'module'
    }
  }
})

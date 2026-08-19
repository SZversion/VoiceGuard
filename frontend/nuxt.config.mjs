export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt'],
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
        }
      ]
    }
  }
})

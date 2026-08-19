<script setup lang="ts">
const route = useRoute()

const navigation = [
  { label: '통화 업로드', to: '/', icon: '↥' },
  { label: '분석 진행', to: '/analyze', icon: '∿' },
  { label: '분석 결과', to: '/result', icon: '▥' },
  { label: '설정', to: '/settings', icon: '⚙' },
  { label: '개인정보 보호 안내', to: '/privacy', icon: '▢' },
  { label: '도움말', to: '/help', icon: '?' }
]
</script>

<template>
  <div class="min-h-screen bg-slate-50 lg:flex">
    <aside class="w-full bg-brand-900 text-white lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
      <div class="px-6 py-8 lg:px-7">
        <NuxtLink to="/" class="block text-2xl font-extrabold leading-tight tracking-tight">
          보이스피싱<br />통화 분석 MVP
        </NuxtLink>
      </div>

      <nav class="flex gap-2 overflow-x-auto px-4 pb-4 lg:block lg:space-y-2 lg:px-4">
        <NuxtLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="flex min-w-max items-center gap-3 rounded-md px-4 py-3 text-sm font-semibold transition"
          :class="route.path === item.to ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-white/10'"
        >
          <span class="flex h-6 w-6 items-center justify-center text-lg" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </NuxtLink>
      </nav>
    </aside>

    <main class="min-h-screen w-full lg:ml-72">
      <div class="mx-auto max-w-6xl px-5 py-6 sm:px-8 sm:py-10">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup>
import {
  ArrowUpTrayIcon,
  ChartBarIcon,
  ChartBarSquareIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()

const navigation = [
  { label: '통화 업로드', to: '/', icon: ArrowUpTrayIcon },
  { label: '분석 진행', to: '/analyze', icon: ChartBarIcon },
  { label: '분석 결과', to: '/result', icon: ChartBarSquareIcon },
  { label: '개인정보 보호 안내', to: '/privacy', icon: ShieldCheckIcon },
  { label: '도움말', to: '/help', icon: QuestionMarkCircleIcon },
]
</script>

<template>
  <div class="min-h-screen bg-slate-50 lg:flex">
    <aside class="w-full bg-brand-900 text-white lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
      <div class="px-6 py-12 lg:px-7">
        <NuxtLink to="/" class="block text-3xl font-bold leading-tight tracking-tight">
          보이스피싱<br />통화 분석 MVP
        </NuxtLink>
      </div>

      <nav class="flex gap-2 overflow-x-auto px-4 pb-4 lg:block lg:space-y-2 lg:px-4">
        <NuxtLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="flex min-w-max items-center gap-3 rounded-md px-4 py-3 text-base font-semibold transition"
          :class="route.path === item.to ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-white/10'"
        >
          <component :is="item.icon" class="h-6 w-6 shrink-0" aria-hidden="true" />
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

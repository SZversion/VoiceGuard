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
    <aside class="mb-8 w-full bg-brand-900 text-white lg:mb-0 lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
      <div class="px-6 py-12 lg:px-7">
        <NuxtLink to="/" class="block text-3xl font-bold leading-tight tracking-tight">
          보이스피싱<br />통화 분석 MVP
        </NuxtLink>
      </div>

      <nav class="grid grid-cols-2 gap-2 overflow-visible px-5 pb-4 sm:grid-cols-3 sm:px-6 lg:block lg:space-y-2 lg:px-4">
        <NuxtLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="flex min-w-0 items-center justify-start gap-2 rounded-md px-2 py-2 text-left text-xs font-semibold leading-tight transition sm:gap-2 sm:px-3 sm:py-2.5 sm:text-sm lg:min-w-max lg:gap-3 lg:px-4 lg:py-3 lg:text-base lg:text-left"
          :class="route.path === item.to ? 'bg-blue-600 text-white' : 'text-slate-200 hover:bg-white/10'"
        >
          <component :is="item.icon" class="h-5 w-5 shrink-0 sm:h-5 sm:w-5 lg:h-6 lg:w-6" aria-hidden="true" />
          <span class="min-w-0">{{ item.label }}</span>
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

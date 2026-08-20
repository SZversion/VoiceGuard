<script setup>
import {
  ArrowUpTrayIcon,
  ArrowUpIcon,
  ChartBarIcon,
  ChartBarSquareIcon,
  EllipsisHorizontalIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const isMoreMenuOpen = ref(false)

const navigation = [
  { label: '통화 업로드', to: '/', icon: ArrowUpTrayIcon },
  { label: '분석 진행', to: '/analyze', icon: ChartBarIcon },
  { label: '분석 결과', to: '/result', icon: ChartBarSquareIcon },
  { label: '개인정보 보호 안내', to: '/privacy', icon: ShieldCheckIcon },
  { label: '도움말', to: '/help', icon: QuestionMarkCircleIcon },
]

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function closeMoreMenu() {
  isMoreMenuOpen.value = false
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 lg:flex">
    <aside class="relative mb-8 h-[100px] w-full bg-brand-900 text-white sm:h-auto lg:mb-0 lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
      <div class="flex h-full items-center justify-between px-6 sm:h-auto sm:items-start sm:px-6 sm:py-12 lg:px-7">
        <NuxtLink to="/" class="block text-3xl font-bold leading-tight tracking-tight">
          <span class="sm:hidden">Voice Guide</span>
          <span class="hidden sm:inline">보이스피싱<br />통화 분석 MVP</span>
        </NuxtLink>

        <button
          type="button"
          class="mt-1 rounded-md p-2 text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-300 sm:hidden"
          aria-label="추가 메뉴 열기"
          :aria-expanded="isMoreMenuOpen"
          @click="isMoreMenuOpen = !isMoreMenuOpen"
        >
          <EllipsisHorizontalIcon class="h-7 w-7" aria-hidden="true" />
        </button>
      </div>

      <div v-if="isMoreMenuOpen" class="absolute right-4 top-20 z-50 w-52 rounded-lg bg-white p-2 text-slate-800 shadow-xl ring-1 ring-slate-200 sm:hidden">
        <NuxtLink
          v-for="item in navigation.slice(3)"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-md px-3 py-3 text-sm font-semibold hover:bg-blue-50"
          @click="closeMoreMenu"
        >
          <component :is="item.icon" class="h-5 w-5 shrink-0 text-blue-600" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </NuxtLink>
      </div>

      <nav class="hidden grid-cols-2 gap-2 overflow-visible px-5 pb-4 sm:grid sm:grid-cols-3 sm:px-6 lg:block lg:space-y-2 lg:px-4">
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
      <div
        class="mx-auto max-w-6xl px-5 pb-[100px] pt-6 sm:px-8 sm:py-10"
        :class="route.path === '/analyze' ? 'pt-0 sm:pt-10' : ''"
      >
        <slot />
      </div>
    </main>

    <button
      v-if="route.path !== '/'"
      type="button"
      class="fixed bottom-5 right-5 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 lg:hidden"
      aria-label="페이지 맨 위로 이동"
      title="맨 위로 이동"
      @click="scrollToTop"
    >
      <ArrowUpIcon class="h-5 w-5" aria-hidden="true" />
    </button>
  </div>
</template>

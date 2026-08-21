<script setup>
import {
  ArrowRightIcon,
  ArrowUpTrayIcon,
  ClipboardDocumentCheckIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  MagnifyingGlassIcon,
  CloudArrowUpIcon,
} from '@heroicons/vue/24/outline'

const reasons = [
  {
    title: '통화 중에는 위험을 알아채기 어렵습니다',
    description: '그럴듯하고 급박한 말에 의심하기 어렵습니다.',
    icon: ExclamationCircleIcon,
  },
  {
    title: '통화가 끝나도 확인이 막막합니다',
    description: '어떤 대화가 위험했는지 찾기 어렵습니다.',
    icon: MagnifyingGlassIcon,
  },
  {
    title: '그래서 다시 확인할 수 있도록 만들어졌습니다',
    description: '의심 구간과 대응 방법을 안내합니다.',
    icon: ClipboardDocumentCheckIcon,
  },
]

const steps = [
  { number: 1, title: '통화 업로드', description: '녹음 파일 선택' },
  { number: 2, title: 'AI 분석', description: '위험 신호 확인' },
  { number: 3, title: '결과 확인', description: '대응 방법 확인' },
]
</script>

<template>
  <div class="space-y-5 sm:space-y-6">
    <section class="rounded-2xl border border-blue-200 bg-blue-50/40 px-6 py-8 sm:px-10 sm:py-12 lg:px-14 lg:py-14">
      <div class="max-w-3xl">
        <h1 class="text-3xl font-extrabold leading-tight tracking-tight text-brand-900 sm:text-4xl lg:text-5xl">
          통화 내용을 분석해<br />위험 신호를 확인하세요
        </h1>
        <p class="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
          녹음 파일을 업로드하면 AI가 통화 내용을 분석하고,<br class="hidden sm:block" />
          확인이 필요한 대화 구간을 안내합니다.
        </p>
        <div class="mt-7 flex flex-col items-stretch gap-4 sm:flex-row sm:items-center">
          <NuxtLink
            to="/upload"
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 text-base font-extrabold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
          >
            <CloudArrowUpIcon class="h-6 w-6" aria-hidden="true" />
            <span>통화 분석 시작하기</span>
          </NuxtLink>
          <NuxtLink
            to="/help"
            class="inline-flex items-center justify-center gap-2 px-2 py-2 text-base font-extrabold text-blue-700 transition hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 sm:justify-start"
          >
            <span>서비스 이용 방법 보기</span>
            <ArrowRightIcon class="h-5 w-5" aria-hidden="true" />
          </NuxtLink>
        </div>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white px-6 py-7 shadow-sm sm:px-7 sm:py-8">
      <h2 class="text-2xl font-extrabold tracking-tight text-brand-900 sm:text-3xl">왜 이 서비스가 필요할까요?</h2>
      <div class="mt-6 grid gap-4 lg:grid-cols-3">
        <article
          v-for="reason in reasons"
          :key="reason.title"
          class="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"
        >
          <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <component :is="reason.icon" class="h-9 w-9" aria-hidden="true" />
          </span>
          <div>
            <h3 class="text-base font-extrabold leading-6 text-brand-900 sm:text-lg">{{ reason.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-500 sm:text-base">{{ reason.description }}</p>
          </div>
        </article>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white px-6 py-7 shadow-sm sm:px-7 sm:py-8">
      <h2 class="text-2xl font-extrabold tracking-tight text-brand-900 sm:text-3xl">이용 방법</h2>
      <p class="mt-2 text-sm leading-6 text-slate-500 sm:text-base">통화 파일을 업로드하면 분석 결과와 대응 방법을 확인할 수 있습니다.</p>

      <ol class="mt-7 grid gap-7 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-center">
        <template v-for="(step, index) in steps" :key="step.number">
          <li class="flex items-center gap-4 lg:justify-center">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-lg font-extrabold text-white">
              {{ step.number }}
            </span>
            <div>
              <h3 class="text-lg font-extrabold text-brand-900">{{ step.title }}</h3>
              <p class="mt-1 text-sm text-slate-500 sm:text-base">{{ step.description }}</p>
            </div>
          </li>
          <span v-if="index < steps.length - 1" class="hidden border-t border-dashed border-slate-300 lg:block" aria-hidden="true" />
        </template>
      </ol>
    </section>

    <aside class="flex items-center gap-4 rounded-2xl border border-blue-200 bg-blue-50/40 px-6 py-5 text-brand-900 sm:px-7">
      <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600">
        <InformationCircleIcon class="h-7 w-7" aria-hidden="true" />
      </span>
      <p class="text-sm font-bold leading-6 sm:text-base">AI 분석 결과는 참고 정보이며, 법적·수사적 확정 판정이 아닙니다.</p>
    </aside>

    <NuxtLink
      to="/upload"
      class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 text-base font-extrabold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 sm:hidden"
    >
      <ArrowUpTrayIcon class="h-5 w-5" aria-hidden="true" />
      <span>통화 업로드로 이동</span>
    </NuxtLink>
  </div>
</template>

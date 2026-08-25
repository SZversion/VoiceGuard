<script setup>
import {
  ArrowPathIcon,
  CheckIcon,
  CloudArrowUpIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from '@heroicons/vue/24/outline'
import {
  PhoneIcon as SolidPhoneIcon,
  ShieldCheckIcon as SolidShieldCheckIcon
} from '@heroicons/vue/24/solid'

const principles = [
  '분석에 필요한 동안만 임시 처리',
  '분석 완료 또는 오류 발생 직후 삭제',
  '분석 이력과 원본 음성 저장 안 함',
  '외부 서비스로 임의 전송하지 않음'
]

const processSteps = [
  { number: 1, title: '파일 업로드', description: '사용자가 통화 녹음 파일을 업로드합니다.' },
  { number: 2, title: '임시 분석', description: '파일을 안전한 환경에서 임시로 처리합니다.' },
  { number: 3, title: 'STT·위험도 분석', description: '음성 전사와 위험도 분석을 수행합니다.' },
  { number: 4, title: '결과 표시', description: '분석 결과를 화면에 표시합니다.' },
  { number: 5, title: '원본·전사문 삭제', description: '분석 완료 또는 오류 발생 직후 삭제합니다.' }
]
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header>
      <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">개인정보 보호 안내</h1>
      <p class="mt-3 text-slate-500">업로드한 통화 녹음파일은 분석 목적으로만 임시 처리됩니다.</p>
    </header>

    <section class="border border-slate-200 bg-white p-6 shadow-[0_1px_5px_rgba(15,23,42,0.15)] sm:p-8">
      <div class="flex items-start gap-5">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center bg-blue-50 text-blue-700">
          <ShieldCheckIcon class="h-10 w-10" aria-hidden="true" />
        </span>

        <div class="min-w-0 flex-1">
          <h2 class="text-2xl font-extrabold text-slate-900 max-[639px]:mt-4">핵심 보호 원칙</h2>
          <ul class="mt-5 divide-y divide-slate-100 max-[639px]:-ml-[84px] max-[639px]:w-[calc(100%+84px)]">
            <li
              v-for="principle in principles"
              :key="principle"
              class="flex min-h-[54px] items-center justify-start gap-4 py-3 text-left text-[16px] font-semibold text-slate-700 max-[639px]:pl-8"
            >
              <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                <CheckIcon class="h-3 w-3" stroke-width="3" aria-hidden="true" />
              </span>
              <span>{{ principle }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div class="flex items-start gap-5">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center bg-blue-50 text-blue-600">
          <ArrowPathIcon class="h-10 w-10" aria-hidden="true" />
        </span>
        <div class="w-full">
          <h2 class="text-2xl font-extrabold text-slate-900 max-[639px]:mt-4">처리 과정</h2>
          <ol class="relative mt-8 grid grid-cols-5 gap-3 before:absolute before:left-[8%] before:right-[8%] before:top-5 before:border-t-2 before:border-dashed before:border-blue-300 max-[640px]:-ml-[84px] max-[640px]:w-[calc(100%+84px)] max-[640px]:grid-cols-1 max-[640px]:gap-7 max-[640px]:before:hidden">
            <li v-for="step in processSteps" :key="step.number" class="relative z-10 min-w-0 text-center">
              <span class="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">{{ step.number }}</span>
              <p class="mt-3 font-bold text-slate-800">{{ step.title }}</p>
              <p class="mt-1 text-sm leading-5 text-slate-500">{{ step.description }}</p>
            </li>
          </ol>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-amber-200 bg-amber-50 p-6 shadow-sm sm:p-8">
      <div class="flex items-start gap-4">
        <ExclamationTriangleIcon class="h-9 w-9 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <h2 class="text-xl font-extrabold text-slate-900 max-[639px]:mt-1">꼭 알아두세요</h2>
          <p class="mt-3 leading-7 text-slate-700">이 서비스는 AI 기반 분석을 제공하며, 법적 판단을 대체하지 않습니다.</p>
          <p class="text-slate-700">최종 판단과 책임은 사용자 본인에게 있습니다.</p>
        </div>
      </div>
    </section>

    <section class="flex flex-col gap-6 border border-blue-100 bg-blue-50 p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:px-8 sm:py-5">
      <div class="flex items-center gap-4">
        <img src="/images/icons/police_icon.png" alt="경찰 신고 안내" class="h-12 w-12 shrink-0 object-contain" />
        <p class="max-w-[190px] text-base font-bold leading-6 text-slate-800">
          위험하거나 피해가 의심되는<br />
          경우 즉시 신고하세요.
        </p>
      </div>

      <div class="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:gap-4">
        <a
          href="tel:112"
          class="flex min-w-[150px] items-center gap-3 border border-slate-200 bg-white px-5 py-3 shadow-sm transition hover:border-blue-300 max-[639px]:min-w-0 max-[639px]:px-3"
        >
          <SolidPhoneIcon class="h-8 w-8 text-blue-600" aria-hidden="true" />
          <span>
            <span class="block text-xs text-slate-500">경찰청</span>
            <span class="block text-2xl font-extrabold leading-7 text-blue-700">112</span>
          </span>
        </a>

        <a
          href="tel:1332"
          class="flex min-w-[150px] items-center gap-3 border border-slate-200 bg-white px-5 py-3 shadow-sm transition hover:border-blue-300 max-[639px]:min-w-0 max-[639px]:px-3"
        >
          <SolidShieldCheckIcon class="h-8 w-8 text-blue-600" aria-hidden="true" />
          <span>
            <span class="block text-xs text-slate-500">금융감독원</span>
            <span class="block text-2xl font-extrabold leading-7 text-blue-700">1332</span>
          </span>
        </a>
      </div>

      <NuxtLink
        to="/"
        class="inline-flex items-center justify-center gap-2 bg-blue-600 px-6 py-4 font-bold text-white shadow-sm transition hover:bg-blue-700"
      >
        <CloudArrowUpIcon class="h-6 w-6" aria-hidden="true" />
        통화 업로드로 이동
      </NuxtLink>
    </section>
  </div>
</template>

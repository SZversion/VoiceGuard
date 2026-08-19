<script setup>
import { ArrowUpTrayIcon, DocumentArrowUpIcon, QuestionMarkCircleIcon } from '@heroicons/vue/24/outline'

const usageSteps = [
  { number: 1, title: '파일 업로드', description: 'WAV, MP3, M4A 통화 녹음 파일을 선택합니다.', icon: ArrowUpTrayIcon },
  { number: 2, title: '분석 시작', description: '분석 시작 버튼을 눌러 분석을 요청합니다.', icon: DocumentArrowUpIcon },
  { number: 3, title: '결과 확인', description: '위험 구간과 대응 안내를 확인합니다.', icon: QuestionMarkCircleIcon }
]

const faqs = [
  { question: '지원하는 파일 형식은 무엇인가요?', answer: '현재 WAV, MP3, M4A 형식을 지원합니다.' },
  { question: '업로드한 파일은 저장되나요?', answer: '분석에 필요한 동안만 임시 처리하며, 분석 이력과 원본 음성을 저장하지 않습니다.' },
  { question: '분석에는 얼마나 걸리나요?', answer: '통화 길이와 내용에 따라 달라질 수 있습니다. 분석 진행 화면에서 현재 단계와 예상 시간을 확인할 수 있습니다.' },
  { question: '분석 결과는 법적 판단인가요?', answer: '아닙니다. AI 분석 결과는 참고 정보이며 법적 확정 판정이 아닙니다.' }
]
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header>
      <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">도움말</h1>
      <p class="mt-3 text-slate-500">서비스 사용 방법과 자주 묻는 질문을 확인하세요.</p>
    </header>

    <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <h2 class="text-2xl font-extrabold text-slate-900">사용 방법</h2>
      <ol class="mt-6 grid gap-6 sm:grid-cols-3">
        <li v-for="step in usageSteps" :key="step.number" class="rounded-lg border border-slate-100 bg-slate-50 p-5">
          <step.icon class="h-8 w-8 text-blue-600" aria-hidden="true" />
          <div class="mt-4 flex items-center gap-2">
            <span class="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">{{ step.number }}</span>
            <h3 class="font-bold text-slate-800">{{ step.title }}</h3>
          </div>
          <p class="mt-2 text-sm leading-6 text-slate-500">{{ step.description }}</p>
        </li>
      </ol>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div class="flex items-center gap-3">
        <QuestionMarkCircleIcon class="h-8 w-8 text-blue-600" aria-hidden="true" />
        <h2 class="text-2xl font-extrabold text-slate-900">자주 묻는 질문</h2>
      </div>
      <div class="mt-5 divide-y divide-slate-100">
        <details v-for="faq in faqs" :key="faq.question" class="group py-4">
          <summary class="cursor-pointer list-none font-bold text-slate-800 marker:hidden">{{ faq.question }}</summary>
          <p class="mt-3 leading-6 text-slate-500">{{ faq.answer }}</p>
        </details>
      </div>
    </section>

    <section class="rounded-xl border border-blue-200 bg-blue-50 p-6 shadow-sm sm:p-8">
      <div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-xl font-extrabold text-slate-900">긴급 신고·상담 안내</h2>
          <p class="mt-2 text-sm text-slate-600">위험하거나 피해가 의심되는 경우 관련 기관에 직접 문의하세요.</p>
        </div>
        <div class="flex flex-wrap gap-3">
          <a href="tel:112" class="inline-flex items-center gap-2 border border-blue-200 bg-white px-5 py-3 font-bold text-blue-700 shadow-sm hover:bg-blue-50">경찰청 112</a>
          <a href="tel:1332" class="inline-flex items-center gap-2 border border-blue-200 bg-white px-5 py-3 font-bold text-blue-700 shadow-sm hover:bg-blue-50">금융감독원 1332</a>
        </div>
      </div>
    </section>

    <div class="text-center">
      <NuxtLink to="/" class="inline-flex items-center gap-2 bg-blue-600 px-6 py-3 font-bold text-white hover:bg-blue-700">통화 업로드로 이동</NuxtLink>
    </div>
  </div>
</template>

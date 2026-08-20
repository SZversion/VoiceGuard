<script setup>
import {
  ArrowPathIcon,
  ArrowUpTrayIcon,
  BookOpenIcon,
  ChartBarIcon,
  ChartBarSquareIcon,
  ChatBubbleLeftEllipsisIcon,
  ChevronDownIcon,
  CloudArrowUpIcon,
  DocumentTextIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
  SignalIcon
} from '@heroicons/vue/24/outline'
import {
  PhoneIcon as SolidPhoneIcon,
  ShieldCheckIcon as SolidShieldCheckIcon
} from '@heroicons/vue/24/solid'

const usageSteps = [
  { number: 1, title: '통화 업로드 메뉴 선택', description: "좌측 메뉴에서 '통화 업로드'를 선택합니다.", icon: ArrowUpTrayIcon },
  { number: 2, title: '녹음파일 선택', description: '음성파일을 선택하고 업로드합니다.', icon: DocumentTextIcon },
  { number: 3, title: '분석 시작', description: '업로드가 완료되면 분석이 자동으로 시작됩니다.', icon: SignalIcon },
  { number: 4, title: '분석 진행 상태 확인', description: '분석 진행 상태와 예상 완료 시간을 확인합니다.', icon: ArrowPathIcon },
  { number: 5, title: '분석 결과와 대응 방법 확인', description: '분석 결과와 위험 구간, 대응 방법을 확인합니다.', icon: ChartBarSquareIcon }
]

const resultGuides = [
  { title: '위험도', description: '통화 전체의 보이스피싱 의심도를 5단계로 제공합니다.', icon: ShieldCheckIcon },
  { title: '위험 구간', description: '보이스피싱 의심이 높은 구간을 타임라인에 표시합니다.', icon: SignalIcon },
  { title: '참고 판정', description: '전체 판정은 참고용이며, 최종 판단은 사용자 본인에게 있습니다.', icon: DocumentTextIcon }
]

const questions = [
  { question: '어떤 파일 형식이 지원되나요?', answer: 'WAV, MP3, M4A 형식의 음성 파일을 지원합니다. 파일 크기 제한은 서비스 안내에 표시된 기준을 따릅니다.' },
  { question: '업로드한 파일은 안전하게 보관되나요?', answer: '업로드한 파일은 분석 목적으로만 임시 처리되며, 분석 완료 또는 오류 발생 후 삭제됩니다.' },
  { question: '분석 결과는 법적 증거로 사용할 수 있나요?', answer: '분석 결과는 참고용 안내이며 법적 판단이나 수사 결과를 대신하지 않습니다. 필요한 경우 관련 기관에 확인하세요.' },
  { question: '분석에는 시간이 얼마나 걸리나요?', answer: '파일의 길이와 분석 상태에 따라 달라질 수 있습니다. 분석 진행 화면에서 예상 완료 시간을 확인할 수 있습니다.' }
]
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-7">
    <header>
      <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">도움말</h1>
      <p class="mt-2 text-slate-500">음성파일을 업로드하고 분석 결과를 확인하는 방법을 안내합니다.</p>
    </header>

    <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div class="flex items-center gap-4">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
          <BookOpenIcon class="h-11 w-11" aria-hidden="true" />
        </span>
        <h2 class="text-2xl font-extrabold text-slate-900">사용 방법</h2>
      </div>

      <ol class="relative mt-10 grid grid-cols-5 gap-3 before:absolute before:left-[10%] before:right-[10%] before:top-5 before:border-t-2 before:border-dashed before:border-blue-200 max-[640px]:grid-cols-1 max-[640px]:gap-7 max-[640px]:before:hidden">
        <li v-for="step in usageSteps" :key="step.number" class="relative z-10 min-w-0 text-center">
          <span class="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-bold text-white">{{ step.number }}</span>
          <component :is="step.icon" class="mx-auto mt-5 h-7 w-7 text-blue-600" aria-hidden="true" />
          <h3 class="mt-3 text-sm font-bold leading-5 text-slate-800">{{ step.title }}</h3>
          <p class="mt-1 text-sm leading-5 text-slate-500">{{ step.description }}</p>
        </li>
      </ol>
    </section>

    <div class="grid gap-7 lg:grid-cols-2">
      <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div class="flex items-center gap-4">
          <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            <ChartBarIcon class="h-11 w-11" aria-hidden="true" />
          </span>
          <h2 class="text-2xl font-extrabold text-slate-900">결과 읽는 방법</h2>
        </div>

        <ul class="mt-7 divide-y divide-slate-100">
          <li v-for="guide in resultGuides" :key="guide.title" class="flex items-start gap-4 py-4 first:pt-0 last:pb-0">
            <component :is="guide.icon" class="mt-1 h-7 w-7 shrink-0 text-blue-600" aria-hidden="true" />
            <div>
              <h3 class="font-bold text-slate-800">{{ guide.title }}</h3>
              <p class="mt-1 text-sm leading-6 text-slate-500">{{ guide.description }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div class="flex items-center gap-4">
          <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            <QuestionMarkCircleIcon class="h-11 w-11" aria-hidden="true" />
          </span>
          <h2 class="text-2xl font-extrabold text-slate-900">자주 묻는 질문</h2>
        </div>

        <div class="mt-7 divide-y divide-slate-100">
          <details v-for="item in questions" :key="item.question" class="group py-4 first:pt-0 last:pb-0">
            <summary class="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-slate-800 [&::-webkit-details-marker]:hidden">
              {{ item.question }}
              <ChevronDownIcon class="h-5 w-5 shrink-0 text-slate-500 transition group-open:rotate-180" aria-hidden="true" />
            </summary>
            <p class="mt-3 pr-8 text-sm leading-6 text-slate-500">{{ item.answer }}</p>
          </details>
        </div>
      </section>
    </div>

    <section class="flex flex-col gap-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center md:justify-between md:p-8">
      <div class="flex items-center gap-4">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
          <ChatBubbleLeftEllipsisIcon class="h-11 w-11" aria-hidden="true" />
        </span>
        <div>
          <h2 class="text-xl font-extrabold text-slate-900">도움이 필요하신가요?</h2>
          <p class="mt-1 text-sm text-slate-500">보이스피싱이 의심되는 경우, 즉시 관련 기관에 신고하세요.</p>
        </div>
      </div>

      <div class="flex w-full flex-col items-center gap-4 md:w-auto md:items-center">
        <div class="flex items-center gap-4">
          <a href="tel:112" class="flex items-center gap-2 text-blue-700" aria-label="경찰청 112 전화하기">
            <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-50">
              <SolidPhoneIcon class="h-6 w-6" aria-hidden="true" />
            </span>
            <span><span class="block text-xs text-slate-500">경찰청</span><strong class="text-xl">112</strong></span>
          </a>
          <a href="tel:1332" class="flex items-center gap-2 text-blue-700 px-8" aria-label="금융감독원 1332 전화하기">
            <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-50">
              <SolidShieldCheckIcon class="h-6 w-6" aria-hidden="true" />
            </span>
            <span><span class="block text-xs text-slate-500">금융감독원</span><strong class="text-xl">1332</strong></span>
          </a>
        </div>
        <NuxtLink to="/" class="mt-2 inline-flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 font-bold text-white transition hover:bg-blue-700 md:mt-0">
          <CloudArrowUpIcon class="h-5 w-5" aria-hidden="true" />
          통화 업로드로 이동
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup>
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  LockClosedIcon,
  ShieldExclamationIcon,
  ShieldCheckIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const { mode, getAnalysisResult } = useAnalysisApi()
const analysisStore = useAnalysisStore()

const errorMessage = ref('')
const isLoading = ref(!analysisStore.hasResult)

const jobId = computed(() => String(route.query.job_id || analysisStore.currentJobId || ''))
const resultData = computed(() => analysisStore.result?.result || analysisStore.result || {})
const score = computed(() => {
  const directScore = resultData.value.score ?? resultData.value.risk_score
  const rawScore = directScore ?? resultData.value.suspicion_score
  const numericScore = Number(rawScore ?? 0)

  if (!Number.isFinite(numericScore)) return 0
  if (directScore == null) return Math.round(numericScore * 10000) / 100
  return numericScore
})
const label = computed(() => resultData.value.label || (score.value >= 50 ? '보이스피싱 의심' : '정상 통화'))
const isSuspicious = computed(() => label.value.includes('의심') || score.value >= 50)
const riskLevel = computed(() => Number(resultData.value.risk_level || (isSuspicious.value ? 5 : 1)))
const riskLabel = computed(() => resultData.value.risk_level_label || (isSuspicious.value ? '매우 높음' : '낮음'))
const segments = computed(() => {
  const source = resultData.value.segments ?? resultData.value.reference_segments
  return Array.isArray(source) ? source.slice(0, 3) : []
})
const immediateActions = [
  '송금하거나 인증번호를 전달하지 마세요.',
  '상대방이 알려준 번호로 다시 전화하지 마세요.',
  '가족이나 주변 사람에게 상황을 알리세요.',
  '공식 기관 번호로 직접 확인하세요.'
]
const defaultAdvice = [
  '어떤 이유로도 송금과 계좌이체를 하지 마세요.',
  '의심되는 경우 말을 잇지 말고 즉시 전화를 끊으세요.',
  '가족 또는 공식기관에 직접 연락해서 사실을 확인하세요.'
]
const advice = computed(() => {
  if (Array.isArray(resultData.value.advice) && resultData.value.advice.length) {
    return resultData.value.advice
  }
  return defaultAdvice
})

async function loadResult() {
  if (analysisStore.hasResult && analysisStore.currentJobId === jobId.value) {
    isLoading.value = false
    return
  }

  if (!jobId.value) {
    errorMessage.value = '분석 작업 번호를 찾을 수 없습니다. 분석 진행 화면에서 다시 확인해주세요.'
    isLoading.value = false
    return
  }

  try {
    const response = await getAnalysisResult(jobId.value)
    analysisStore.setResult(jobId.value, response)
  } catch {
    errorMessage.value = '분석 결과를 불러오지 못했습니다. 분석이 완료되었는지 확인해주세요.'
  } finally {
    isLoading.value = false
  }
}

function goToUpload() {
  analysisStore.clear()
  router.push('/upload')
}

function formatSuspicionScore(value) {
  const numericScore = Number(value)
  if (!Number.isFinite(numericScore)) return '-'
  return `${(numericScore * 100).toFixed(2)}%`
}

function levelClass(level) {
  return level >= 4 ? 'bg-red-100 text-red-700' : level >= 3 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
}

onMounted(loadResult)
</script>

<template>
  <div>
    <WorkflowSteps :current="3" />

    <div v-if="isLoading" class="max-w-5xl p-10 mx-auto text-center bg-white border shadow-sm rounded-xl border-slate-200 text-slate-500">
      분석 결과를 불러오는 중입니다.
    </div>

    <!-- 에러 메시지 -->
    <div v-else-if="errorMessage" class="max-w-3xl p-6 mx-auto text-red-800 border border-red-200 rounded-xl bg-red-50">
      <div class="flex items-start gap-3">
        <ExclamationTriangleIcon class="w-6 h-6 shrink-0" aria-hidden="true" />
        <div>
          <p class="font-bold">결과를 표시할 수 없습니다.</p>
          <p class="mt-2 text-sm">{{ errorMessage }}</p>
          <button type="button" class="mt-4 font-bold text-blue-700 underline" @click="goToUpload">업로드 화면으로 돌아가기</button>
        </div>
      </div>
    </div>

    <div v-else class="max-w-5xl mx-auto space-y-6">

      <!-- 분석 결과 -->
      <section class="sm:hidden">
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900">분석 결과</h1>
        <p class="mt-2 text-sm leading-6 text-slate-500">업로드한 통화 내용을 분석한 결과를 안내합니다.</p>
      </section>

      <!-- 분석 결과 -->
      <section
        class="flex flex-col gap-5 p-6 border shadow-sm rounded-xl sm:flex-row sm:items-center sm:justify-between sm:p-8"
        :class="isSuspicious ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'"
      >
        <div class="flex items-center gap-5">
          <span class="flex items-center justify-center w-20 h-20 rounded-full shrink-0" :class="isSuspicious ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'">
            <ShieldExclamationIcon v-if="isSuspicious" class="w-12 h-12" aria-hidden="true" />
            <ShieldCheckIcon v-else class="w-12 h-12" aria-hidden="true" />
          </span>
          <div>
            <p class="text-3xl font-extrabold" :class="isSuspicious ? 'text-red-700' : 'text-emerald-700'">{{ label }}</p>
            <p class="mt-1 text-sm text-slate-600">위험 점수 (Risk Score)</p>
            <div class="flex items-center gap-3 mt-1">
              <span class="text-4xl font-extrabold" :class="isSuspicious ? 'text-red-700' : 'text-emerald-700'">{{ score }}%</span>
              <span class="px-3 py-1 text-sm font-bold rounded-full" :class="levelClass(riskLevel)">{{ riskLabel }}</span>
            </div>
          </div>
        </div>
        <div class="max-w-sm text-sm leading-6 text-slate-700 sm:text-right">
          <p>{{ resultData.summary?.description || '분석 결과를 확인해주세요.' }}</p>
          <p class="mt-2 font-bold text-red-600">※ {{ resultData.disclaimer || '본 결과는 법적 확정 판정이 아닌 참고 정보입니다.' }}</p>
        </div>
      </section>

      <!-- 즉시 행동 안내 -->
      <section v-if="score >= 50" class="mt-10 overflow-hidden bg-white border shadow-sm rounded-xl border-slate-200">
        <div class="px-6 pt-10 pb-4 sm:px-8">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-[26px] font-extrabold text-slate-900">즉시 행동 안내</h2>
            <span class="px-3 py-1 text-xs font-bold text-blue-700 rounded-full bg-blue-50">위험도 50 이상</span>
          </div>
          <p class="mt-1 text-red-500 text-md">위험도가 50 이상인 경우 아래 순서대로 대응하세요.</p>
        </div>
        <ol class="border-t divide-y mb-9 divide-slate-100 border-slate-100">
          <li v-for="(item, index) in immediateActions" :key="item" class="flex items-center gap-4 px-6 py-3.5 sm:px-8">
            <span class="flex items-center justify-center w-6 h-6 text-lg font-bold text-white bg-blue-600 rounded-full shrink-0">{{ index + 1 }}</span>
            <span class="text-lg font-semibold leading-6 text-slate-700">{{ item }}</span>
          </li>
        </ol>
      </section>

      <!-- 위험 구간 -->
      <section class="bg-white border shadow-sm rounded-xl border-slate-200">
        <div class="px-6 py-4 border-b border-slate-200">
          <h2 class="text-xl font-extrabold text-slate-900">위험 구간</h2>
          <p class="mt-1 text-sm text-slate-500">수치·내용(의심 근거)</p>
        </div>
        <div v-if="segments.length" class="divide-y divide-slate-100">
          <article v-for="segment in segments" :key="`${segment.start_time}-${segment.text}`" class="grid gap-3 px-6 py-5 sm:grid-cols-[9rem_1fr]">
            <p class="font-bold text-blue-600">{{ formatSuspicionScore(segment.suspicion_score) }}</p>
            <div>
              <p class="font-bold text-slate-800">“{{ segment.transcript || segment.text || segment.content || '-' }}”</p>
              <p v-if="segment.reason" class="mt-1 text-sm text-slate-500">{{ segment.reason }}</p>
            </div>
          </article>
        </div>
        <div v-else class="flex items-center gap-3 px-6 py-8 text-slate-500">
          <CheckCircleIcon class="w-6 h-6 text-emerald-600" aria-hidden="true" />
          위험 구간이 발견되지 않았습니다.
        </div>
      </section>      

      <!-- 안전하게 대응하세요 -->
      <section class="p-6 border border-blue-200 rounded-xl bg-blue-50 sm:p-8">
        <div class="grid items-center gap-5 sm:grid-cols-[7rem_1fr]">
          <span class="flex items-center justify-center w-20 h-20 mx-auto text-white bg-indigo-500 rounded-full">
            <ShieldCheckIcon class="w-12 h-12" aria-hidden="true" />
          </span>
          <div class="w-full [&>h2]:text-center">
            <h2 class="text-[26px] font-extrabold text-blue-800">안전하게 대응하세요</h2>
            <ol class="grid max-w-sm gap-6 mx-auto mt-5 sm:max-w-none sm:mx-0 sm:grid-cols-3">
              <li v-for="(item, index) in advice" :key="item" class="flex flex-col items-center gap-2 font-medium leading-6 text-center text-slate-700 sm:flex-row sm:items-start sm:gap-3 sm:text-left">
                <span class="flex items-center justify-center w-6 h-6 font-bold text-white bg-blue-600 rounded-full shrink-0">{{ index + 1 }}</span>
                <span class="text-lg font-semibold">{{ item }}</span>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <div class="pt-1 text-center">
        <button
          type="button"
          class="flex items-center justify-center w-full max-w-md px-5 py-4 mx-auto text-lg font-bold text-white transition bg-blue-600 rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
          @click="goToUpload"
        >
          새 통화 분석하기
        </button>
        <p class="flex items-center justify-center gap-2 mt-4 text-base text-slate-600">
          <LockClosedIcon class="w-5 h-5 text-slate-500" aria-hidden="true" />
          <span>분석 완료 후 원본 파일과 전사 내용은 삭제됩니다.</span>
        </p>
      </div>
    </div>
  </div>
</template>

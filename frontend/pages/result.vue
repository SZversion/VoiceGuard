<script setup>
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  ShieldCheckIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const { mode, getAnalysisResult } = useAnalysisApi()

const result = ref(null)
const errorMessage = ref('')
const isLoading = ref(true)

const jobId = computed(() => String(route.query.job_id || ''))
const resultData = computed(() => result.value?.result || result.value || {})
const score = computed(() => Number(resultData.value.score ?? resultData.value.risk_score ?? 0))
const label = computed(() => resultData.value.label || (score.value >= 50 ? '보이스피싱 의심' : '정상 통화'))
const isSuspicious = computed(() => label.value.includes('의심') || score.value >= 50)
const riskLevel = computed(() => Number(resultData.value.risk_level || (isSuspicious.value ? 5 : 1)))
const riskLabel = computed(() => resultData.value.risk_level_label || (isSuspicious.value ? '매우 높음' : '낮음'))
const segments = computed(() => Array.isArray(resultData.value.segments) ? resultData.value.segments.slice(0, 3) : [])
const advice = computed(() => Array.isArray(resultData.value.advice) ? resultData.value.advice : [])

async function loadResult() {
  if (!jobId.value) {
    errorMessage.value = '분석 작업 번호를 찾을 수 없습니다. 분석 진행 화면에서 다시 확인해주세요.'
    isLoading.value = false
    return
  }

  try {
    result.value = await getAnalysisResult(jobId.value)
  } catch {
    errorMessage.value = '분석 결과를 불러오지 못했습니다. 분석이 완료되었는지 확인해주세요.'
  } finally {
    isLoading.value = false
  }
}

function goToUpload() {
  router.push('/')
}

function levelClass(level) {
  return level >= 4 ? 'bg-red-100 text-red-700' : level >= 3 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
}

onMounted(loadResult)
</script>

<template>
  <div>
    <WorkflowSteps :current="3" />

    <div v-if="isLoading" class="mx-auto max-w-5xl rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-500 shadow-sm">
      분석 결과를 불러오는 중입니다.
    </div>

    <div v-else-if="errorMessage" class="mx-auto max-w-3xl rounded-xl border border-red-200 bg-red-50 p-6 text-red-800">
      <div class="flex items-start gap-3">
        <ExclamationTriangleIcon class="h-6 w-6 shrink-0" aria-hidden="true" />
        <div>
          <p class="font-bold">결과를 표시할 수 없습니다.</p>
          <p class="mt-2 text-sm">{{ errorMessage }}</p>
          <button type="button" class="mt-4 font-bold text-blue-700 underline" @click="goToUpload">업로드 화면으로 돌아가기</button>
        </div>
      </div>
    </div>

    <div v-else class="mx-auto max-w-5xl space-y-6">
      <section
        class="flex flex-col gap-5 rounded-xl border p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-8"
        :class="isSuspicious ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'"
      >
        <div class="flex items-center gap-5">
          <span class="flex h-20 w-20 shrink-0 items-center justify-center rounded-full" :class="isSuspicious ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'">
            <ShieldExclamationIcon v-if="isSuspicious" class="h-12 w-12" aria-hidden="true" />
            <ShieldCheckIcon v-else class="h-12 w-12" aria-hidden="true" />
          </span>
          <div>
            <p class="text-3xl font-extrabold" :class="isSuspicious ? 'text-red-700' : 'text-emerald-700'">{{ label }}</p>
            <p class="mt-1 text-sm text-slate-600">위험 점수 (Risk Score)</p>
            <div class="mt-1 flex items-center gap-3">
              <span class="text-4xl font-extrabold" :class="isSuspicious ? 'text-red-700' : 'text-emerald-700'">{{ score }}%</span>
              <span class="rounded-full px-3 py-1 text-sm font-bold" :class="levelClass(riskLevel)">{{ riskLabel }}</span>
            </div>
          </div>
        </div>
        <div class="max-w-sm text-sm leading-6 text-slate-700 sm:text-right">
          <p>{{ resultData.summary?.description || '분석 결과를 확인해주세요.' }}</p>
          <p class="mt-2 font-bold text-red-600">※ {{ resultData.disclaimer || '본 결과는 법적 확정 판정이 아닌 참고 정보입니다.' }}</p>
        </div>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-200 px-6 py-4">
          <h2 class="text-xl font-extrabold text-slate-900">위험 구간</h2>
          <p class="mt-1 text-sm text-slate-500">시간·내용(의심 근거)</p>
        </div>
        <div v-if="segments.length" class="divide-y divide-slate-100">
          <article v-for="segment in segments" :key="`${segment.start_time}-${segment.text}`" class="grid gap-3 px-6 py-5 sm:grid-cols-[9rem_1fr]">
            <p class="font-bold text-blue-600">{{ segment.start_time || segment.start || '-' }}</p>
            <div>
              <p class="font-bold text-slate-800">“{{ segment.text || segment.content || '-' }}”</p>
              <p v-if="segment.reason" class="mt-1 text-sm text-slate-500">{{ segment.reason }}</p>
            </div>
          </article>
        </div>
        <div v-else class="flex items-center gap-3 px-6 py-8 text-slate-500">
          <CheckCircleIcon class="h-6 w-6 text-emerald-600" aria-hidden="true" />
          위험 구간이 발견되지 않았습니다.
        </div>
      </section>

      <section class="rounded-xl border border-blue-200 bg-blue-50 p-6 sm:p-8">
        <div class="grid items-center gap-5 sm:grid-cols-[7rem_1fr]">
          <span class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-indigo-500 text-white">
            <ShieldCheckIcon class="h-12 w-12" aria-hidden="true" />
          </span>
          <div class="w-full [&>h2]:text-center">
            <h2 class="text-2xl font-extrabold text-blue-800">안전하게 대응하세요</h2>
            <ol class="mt-5 grid gap-6 sm:grid-cols-3">
              <li v-for="(item, index) in advice" :key="item" class="flex items-start gap-3 text-sm leading-6 text-slate-700">
                <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 font-bold text-white">{{ index + 1 }}</span>
                <span>{{ item }}</span>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <p class="text-center text-xs text-slate-400">{{ mode === 'mock' ? 'Mock API' : '실제 API' }} 결과 · 작업 번호 {{ jobId }}</p>
    </div>
  </div>
</template>

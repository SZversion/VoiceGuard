<script setup>
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  MusicalNoteIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const { mode, getAnalysisStatus, cancelAnalysis } = useAnalysisApi()

const defaultSteps = [
  { key: 'preprocessing', label: '음성 전처리', description: '잡음 제거 및 음성 품질 개선을 진행합니다.' },
  { key: 'transcribing', label: 'Whisper STT 전사', description: '음성을 텍스트로 변환합니다.' },
  { key: 'normalizing', label: '텍스트 정규화·청킹', description: '텍스트를 정규화하고 분석 단위로 나눕니다.' },
  { key: 'classifying', label: '위험도 분류', description: '통화 내용을 분석하여 위험도를 분류합니다.' },
  { key: 'risk_search', label: '위험 구간 탐색', description: '위험한 표현과 근거 구간을 탐색합니다.' },
  { key: 'finalizing', label: '대응 안내 생성', description: '맞춤형 대응 안내를 생성합니다.' }
]

const jobId = computed(() => String(route.query.job_id || ''))
const analysis = ref(null)
const errorMessage = ref('')
const isLoading = ref(true)
const isCancelling = ref(false)
let pollTimer = null

const terminalStatuses = ['completed', 'failed', 'cancelled']
const status = computed(() => analysis.value?.status || 'queued')
const isTerminal = computed(() => terminalStatuses.includes(status.value))
const steps = computed(() => analysis.value?.steps?.length ? analysis.value.steps : defaultSteps)
const progress = computed(() => Number(analysis.value?.progress || 0))
const currentStage = computed(() => analysis.value?.stage || 'queued')
const currentStepElement = ref(null)

const statusLabel = computed(() => ({
  queued: '분석 준비 중',
  running: '분석 진행 중',
  completed: '분석 완료',
  failed: '분석 실패',
  cancelled: '분석 취소됨'
}[status.value] || '분석 진행 중'))

const statusMessage = computed(() => ({
  queued: '분석을 준비하고 있습니다.',
  running: '안전하고 정확한 분석을 위해 처리하고 있습니다.',
  completed: '분석이 완료되었습니다. 결과를 확인할 수 있습니다.',
  failed: '분석 중 문제가 발생했습니다. 다시 시도해주세요.',
  cancelled: '분석이 취소되었습니다. 분석 결과는 표시하지 않습니다.'
}[status.value] || '분석 진행 상태를 확인하고 있습니다.'))

function formatBytes(bytes) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateTime(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat('ko-KR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function stepState(step) {
  if (step.status) return step.status
  if (status.value === 'completed') return 'completed'
  if (status.value === 'failed' && step.key === currentStage.value) return 'failed'
  const currentIndex = defaultSteps.findIndex((item) => item.key === currentStage.value)
  const stepIndex = defaultSteps.findIndex((item) => item.key === step.key)
  if (stepIndex < currentIndex) return 'completed'
  if (stepIndex === currentIndex) return 'running'
  return 'pending'
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadStatus() {
  if (!jobId.value) {
    isLoading.value = false
    errorMessage.value = '분석 작업 번호를 찾을 수 없습니다. 업로드 화면에서 다시 시작해주세요.'
    return
  }

  try {
    const response = await getAnalysisStatus(jobId.value)
    analysis.value = response
    errorMessage.value = ''
    if (response.status === 'completed') {
      stopPolling()
      await router.replace({ path: '/result', query: { job_id: jobId.value } })
      return
    }
    if (terminalStatuses.includes(response.status)) stopPolling()
  } catch {
    errorMessage.value = '분석 진행 상태를 확인하지 못했습니다. 잠시 후 다시 시도해주세요.'
    stopPolling()
  } finally {
    isLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(loadStatus, 1000)
}

async function handleCancel() {
  if (!jobId.value || isCancelling.value || isTerminal.value) return

  isCancelling.value = true
  try {
    analysis.value = await cancelAnalysis(jobId.value)
    stopPolling()
  } catch {
    errorMessage.value = '분석을 취소하지 못했습니다. 잠시 후 다시 시도해주세요.'
  } finally {
    isCancelling.value = false
  }
}

function goToUpload() {
  router.push('/upload')
}

function setCurrentStepElement(element, step) {
  if (step.key === currentStage.value) currentStepElement.value = element
}

watch(currentStage, async (nextStage, previousStage) => {
  if (!nextStage || nextStage === previousStage) return

  await nextTick()
  if (window.matchMedia('(max-width: 639px)').matches) {
    currentStepElement.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
})

onMounted(async () => {
  await loadStatus()
  if (!isTerminal.value && !errorMessage.value) startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <div>
    <WorkflowSteps :current="2" />

    <div v-if="errorMessage && !analysis" class="mx-auto max-w-3xl rounded-xl border border-red-200 bg-red-50 p-6 text-red-800">
      <div class="flex items-start gap-3">
        <ExclamationTriangleIcon class="h-6 w-6 shrink-0" aria-hidden="true" />
        <div>
          <p class="font-bold">분석 진행 상태를 불러오지 못했습니다.</p>
          <p class="mt-2 text-sm">{{ errorMessage }}</p>
          <button type="button" class="mt-4 font-bold text-blue-700 underline" @click="goToUpload">업로드 화면으로 돌아가기</button>
        </div>
      </div>
    </div>

    <div v-else class="mx-auto max-w-5xl space-y-6">
      <section class="hidden items-center gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:flex">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center bg-blue-50 text-blue-600">
          <MusicalNoteIcon class="h-9 w-9" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-lg font-extrabold text-slate-900">{{ analysis?.file_name || '업로드된 통화 파일' }}</p>
          <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-500">
            <span v-if="analysis?.uploaded_at"><ClockIcon class="mr-1 inline h-4 w-4" aria-hidden="true" />업로드 시간 {{ formatDateTime(analysis.uploaded_at) }}</span>
            <span v-if="analysis?.file_size">용량 {{ formatBytes(analysis.file_size) }}</span>
            <span>작업 번호 {{ jobId }}</span>
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div class="flex items-end justify-between gap-4">
          <h1 class="text-2xl font-extrabold text-slate-900">분석 진행률</h1>
          <span class="text-3xl font-extrabold text-blue-600">{{ progress }}%</span>
        </div>
        <div class="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
          <div class="h-full rounded-full bg-blue-600 transition-all duration-500" :style="{ width: `${progress}%` }" />
        </div>
        <div class="mt-3 flex justify-between gap-4 text-sm text-slate-500">
          <span v-if="analysis?.estimated_seconds && !isTerminal">예상 완료 시간 {{ Math.floor(analysis.estimated_seconds / 60).toString().padStart(2, '0') }}:{{ (analysis.estimated_seconds % 60).toString().padStart(2, '0') }}</span>
          <span v-else>{{ statusLabel }}</span>
          <span class="hidden sm:block">분석 시간은 통화 길이와 내용에 따라 달라질 수 있습니다.</span>
        </div>

        <div class="mt-8 border-t border-slate-100 pt-6">
          <h2 class="text-xl font-extrabold text-slate-900">분석 단계</h2>
          <ol class="mt-6 space-y-0">
            <li v-for="(step, index) in steps" :key="step.key" :ref="(element) => setCurrentStepElement(element, step)" class="relative flex scroll-mt-6 gap-4 pb-7 last:pb-0">
              <span v-if="index < steps.length - 1" class="absolute left-4 top-9 h-full w-0.5 bg-slate-200" aria-hidden="true" />
              <span
                class="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 bg-white"
                :class="{
                  'border-blue-600 bg-blue-600 text-white': stepState(step) === 'completed',
                  'border-blue-600 text-blue-600': stepState(step) === 'running',
                  'border-red-500 text-red-500': stepState(step) === 'failed',
                  'border-slate-300 text-slate-300': stepState(step) === 'pending'
                }"
              >
                <CheckCircleIcon v-if="stepState(step) === 'completed'" class="h-5 w-5" aria-hidden="true" />
                <ArrowPathIcon v-else-if="stepState(step) === 'running'" class="h-5 w-5 animate-spin" aria-hidden="true" />
                <XCircleIcon v-else-if="stepState(step) === 'failed'" class="h-5 w-5" aria-hidden="true" />
                <span v-else class="h-2 w-2 rounded-full bg-slate-300" />
              </span>
              <div class="flex min-w-0 flex-1 items-start justify-between gap-4">
                <div>
                  <p class="font-bold" :class="stepState(step) === 'running' ? 'text-blue-600' : 'text-slate-800'">{{ step.label }}</p>
                  <p class="mt-1 text-sm text-slate-500">{{ step.description }}</p>
                </div>
                <span class="shrink-0 text-sm font-bold" :class="stepState(step) === 'running' || stepState(step) === 'completed' ? 'text-blue-600' : stepState(step) === 'failed' ? 'text-red-600' : 'text-slate-400'">
                  {{ stepState(step) === 'completed' ? '완료' : stepState(step) === 'running' ? '진행 중' : stepState(step) === 'failed' ? '실패' : '대기' }}
                </span>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <section
        v-if="status !== 'completed'"
        class="flex flex-col gap-3 rounded-xl border p-5 sm:flex-row sm:items-center sm:justify-between"
        :class="status === 'failed' ? 'border-red-200 bg-red-50' : status === 'cancelled' ? 'border-amber-200 bg-amber-50' : status === 'completed' ? 'border-emerald-200 bg-emerald-50' : 'border-blue-100 bg-blue-50'"
      >
        <div class="flex items-start gap-3">
          <ExclamationTriangleIcon v-if="status === 'failed'" class="h-6 w-6 shrink-0 text-red-600" aria-hidden="true" />
          <XCircleIcon v-else-if="status === 'cancelled'" class="h-6 w-6 shrink-0 text-amber-600" aria-hidden="true" />
          <CheckCircleIcon v-else-if="status === 'completed'" class="h-6 w-6 shrink-0 text-emerald-600" aria-hidden="true" />
          <ArrowPathIcon v-else class="h-6 w-6 shrink-0 animate-spin text-blue-600" aria-hidden="true" />
          <div>
            <p class="font-extrabold text-slate-900">{{ statusMessage }}</p>
            <p v-if="errorMessage" class="mt-1 text-sm text-red-700">{{ errorMessage }}</p>
          </div>
        </div>
        <div class="flex shrink-0 gap-2">
          <button v-if="status === 'failed' || status === 'cancelled'" type="button" class="border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" @click="goToUpload">다시 분석하기</button>
          <button v-else type="button" class="border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isCancelling" @click="handleCancel">
            {{ isCancelling ? '취소 중...' : '분석 취소' }}
          </button>
        </div>
      </section>

      <p class="text-center text-xs text-slate-400">{{ mode === 'mock' ? 'Mock API' : '실제 API' }}로 분석 상태를 확인하고 있습니다.</p>
    </div>
  </div>
</template>

<script setup>
const router = useRouter()
const { createAnalysis, mode } = useAnalysisApi()

const selectedFile = ref(null)
const errorMessage = ref('')
const isSubmitting = ref(false)

const canStart = computed(() => selectedFile.value && !isSubmitting.value)

function selectFile(file) {
  selectedFile.value = file
  errorMessage.value = ''
}

function showFileError(message) {
  selectedFile.value = null
  errorMessage.value = message
}

function removeFile() {
  selectedFile.value = null
  errorMessage.value = ''
}

async function startAnalysis() {
  if (!canStart.value) return

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const response = await createAnalysis(selectedFile.value)
    await router.push({ path: '/analyze', query: { job_id: response.job_id } })
  } catch {
    errorMessage.value = '분석을 시작하지 못했습니다. 잠시 후 다시 시도해주세요.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div>
    <WorkflowSteps :current="1" />

    <header class="mx-auto max-w-3xl text-center">
      <h1 class="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">통화 파일을 업로드하세요</h1>
      <p class="mt-3 text-sm text-slate-500 sm:text-base">보이스피싱 분석을 위해 통화 녹음 파일을 업로드해 주세요.</p>
    </header>

    <div class="mx-auto mt-10 max-w-3xl space-y-5">
      <ConsentNotice />
      <AudioUploader @selected="selectFile" @error="showFileError" />
      <FileInfo :file="selectedFile" @remove="removeFile" />

      <p v-if="errorMessage" class="rounded-md bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">
        {{ errorMessage }}
      </p>

      <button
        type="button"
        class="w-full px-6 py-4 text-lg font-extrabold transition disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
        :class="canStart ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-slate-200 text-slate-400'"
        :disabled="!canStart"
        @click="startAnalysis"
      >
        {{ isSubmitting ? '분석 준비 중...' : '분석 시작' }}
      </button>

      <p class="text-center text-xs text-slate-400">SSL 암호화로 안전하게 전송합니다. ({{ mode === 'mock' ? 'Mock API' : '실제 API' }})</p>
    </div>
  </div>
</template>

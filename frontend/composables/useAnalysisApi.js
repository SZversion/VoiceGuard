import { cancelMockAnalysis, createMockAnalysis, getMockAnalysisResult, getMockAnalysisStatus } from '~/mocks/analysisMock'

export function useAnalysisApi() {
  const config = useRuntimeConfig()
  const mode = computed(() => (config.public.useMock ? 'mock' : 'api'))

  async function createAnalysis(file) {
    if (config.public.useMock) return createMockAnalysis(file)

    const formData = new FormData()
    formData.append('audio', file)
    return $fetch('/analyze', {
      method: 'POST',
      baseURL: config.public.apiBase,
      body: formData
    })
  }

  async function getAnalysisStatus(jobId) {
    if (config.public.useMock) return getMockAnalysisStatus(jobId)
    return $fetch(`/analyze/${encodeURIComponent(jobId)}/status`, { baseURL: config.public.apiBase })
  }

  async function cancelAnalysis(jobId) {
    if (config.public.useMock) return cancelMockAnalysis(jobId)
    return $fetch(`/analyze/${encodeURIComponent(jobId)}`, {
      method: 'DELETE',
      baseURL: config.public.apiBase
    })
  }

  async function getAnalysisResult(jobId) {
    if (config.public.useMock) return getMockAnalysisResult(jobId)
    return $fetch(`/analyze/${encodeURIComponent(jobId)}/result`, { baseURL: config.public.apiBase })
  }

  return {
    mode,
    apiBase: computed(() => String(config.public.apiBase)),
    createAnalysis,
    getAnalysisStatus,
    cancelAnalysis,
    getAnalysisResult
  }
}

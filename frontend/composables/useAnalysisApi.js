import { createMockAnalysis } from '~/mocks/analysisMock'

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

  return {
    mode,
    apiBase: computed(() => String(config.public.apiBase)),
    createAnalysis
  }
}

export function useAnalysisApi() {
  const config = useRuntimeConfig()
  const mode = computed(() => (config.public.useMock ? 'mock' : 'api'))

  return {
    mode,
    apiBase: computed(() => String(config.public.apiBase))
    // API 호출은 2단계에서 Mock 계약과 함께 추가한다.
  }
}

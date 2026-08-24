import { defineStore } from 'pinia'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    currentJobId: '',
    result: null
  }),

  getters: {
    hasResult: (state) => Boolean(state.currentJobId && state.result)
  },

  actions: {
    setJobId(jobId) {
      const nextJobId = String(jobId || '')
      if (this.currentJobId !== nextJobId) {
        this.currentJobId = nextJobId
        this.result = null
      }
    },

    setResult(jobId, result) {
      this.currentJobId = String(jobId || '')
      this.result = result
    },

    clear() {
      this.currentJobId = ''
      this.result = null
    }
  }
})

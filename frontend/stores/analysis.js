import { defineStore } from 'pinia'
import { markRaw } from 'vue'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    currentJobId: '',
    result: null,
    selectedFile: null
  }),

  getters: {
    hasResult: (state) => Boolean(state.currentJobId && state.result)
  },

  actions: {
    setSelectedFile(file) {
      this.currentJobId = ''
      this.result = null
      this.selectedFile = file ? markRaw(file) : null
    },

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
      this.selectedFile = null
    }
  }
})

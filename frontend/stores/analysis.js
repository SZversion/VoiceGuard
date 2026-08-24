import { defineStore } from 'pinia'
import { markRaw } from 'vue'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    currentJobId: '',
    result: null,
    selectedFile: null,
    status: '',
    stage: 'queued',
    progress: 0,
    failure: null
  }),

  getters: {
    hasResult: (state) => Boolean(state.currentJobId && state.result)
  },

  actions: {
    setSelectedFile(file) {
      this.currentJobId = ''
      this.result = null
      this.status = ''
      this.stage = 'queued'
      this.progress = 0
      this.failure = null
      this.selectedFile = file ? markRaw(file) : null
    },

    setJobId(jobId) {
      const nextJobId = String(jobId || '')
      if (this.currentJobId !== nextJobId) {
        this.currentJobId = nextJobId
        this.result = null
        this.status = 'queued'
        this.stage = 'queued'
        this.progress = 0
        this.failure = null
      }
    },

    setStatus(jobId, response) {
      this.currentJobId = String(jobId || response?.job_id || '')
      this.status = response?.status || ''
      this.stage = response?.stage || 'queued'
      this.progress = Number.isFinite(Number(response?.progress)) ? Number(response.progress) : 0
      if (this.status !== 'failed') this.failure = null
    },

    setFailure(jobId, message) {
      this.currentJobId = String(jobId || '')
      this.status = 'failed'
      this.stage = 'failed'
      this.failure = { message: message || '분석 중 오류가 발생했습니다.' }
    },

    setResult(jobId, result) {
      this.currentJobId = String(jobId || '')
      this.result = result
      this.status = 'completed'
      this.stage = 'completed'
      this.progress = 100
      this.failure = null
    },

    clear() {
      this.currentJobId = ''
      this.result = null
      this.selectedFile = null
      this.status = ''
      this.stage = 'queued'
      this.progress = 0
      this.failure = null
    }
  }
})

const jobs = new Map()

const mockSteps = [
  { key: 'preprocessing', label: '음성 전처리', description: '잡음 제거 및 음성 품질 개선을 진행합니다.' },
  { key: 'transcribing', label: 'Whisper STT 전사', description: '음성을 텍스트로 변환합니다.' },
  { key: 'normalizing', label: '텍스트 정규화·청킹', description: '텍스트를 정규화하고 분석 단위로 나눕니다.' },
  { key: 'classifying', label: '위험도 분류', description: '통화 내용을 분석하여 위험도를 분류합니다.' },
  { key: 'risk_search', label: '위험 구간 탐색', description: '위험한 표현과 근거 구간을 탐색합니다.' },
  { key: 'finalizing', label: '대응 안내 생성', description: '맞춤형 대응 안내를 생성합니다.' }
]

const progressByStage = {
  queued: 0,
  preprocessing: 15,
  transcribing: 35,
  normalizing: 50,
  classifying: 65,
  risk_search: 82,
  finalizing: 94,
  completed: 100
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function getStage(elapsedSeconds) {
  if (elapsedSeconds < 1) return 'queued'
  if (elapsedSeconds < 3) return 'preprocessing'
  if (elapsedSeconds < 6) return 'transcribing'
  if (elapsedSeconds < 8) return 'normalizing'
  if (elapsedSeconds < 10) return 'classifying'
  if (elapsedSeconds < 12) return 'risk_search'
  if (elapsedSeconds < 14) return 'finalizing'
  return 'completed'
}

function buildSteps(stage, status) {
  const currentIndex = mockSteps.findIndex((step) => step.key === stage)

  return mockSteps.map((step, index) => ({
    ...step,
    status:
      status === 'cancelled' || status === 'failed'
        ? index < currentIndex ? 'completed' : index === currentIndex ? 'failed' : 'pending'
        : stage === 'completed' || index < currentIndex
          ? 'completed'
          : index === currentIndex
            ? 'running'
            : 'pending'
  }))
}

function toResponse(job, now = Date.now()) {
  if (job.status === 'cancelled') {
    return {
      job_id: job.jobId,
      status: 'cancelled',
      stage: job.stage,
      progress: job.progress,
      estimated_seconds: 0,
      file_name: job.fileName,
      file_size: job.fileSize,
      uploaded_at: job.uploadedAt,
      steps: buildSteps(job.stage, 'cancelled')
    }
  }

  const elapsedSeconds = (now - job.createdAt) / 1000
  const stage = getStage(elapsedSeconds)
  const status = stage === 'completed' ? 'completed' : stage === 'queued' ? 'queued' : 'running'
  const progress = progressByStage[stage]

  job.stage = stage
  job.status = status
  job.progress = progress

  return {
    job_id: job.jobId,
    status,
    stage,
    progress,
    estimated_seconds: Math.max(0, Math.ceil(14 - elapsedSeconds)),
    file_name: job.fileName,
    file_size: job.fileSize,
    uploaded_at: job.uploadedAt,
    steps: buildSteps(stage, status)
  }
}

export async function createMockAnalysis(file) {
  await wait(350)

  const jobId = `mock_job_${Date.now()}`
  jobs.set(jobId, {
    jobId,
    createdAt: Date.now(),
    fileName: file.name,
    fileSize: file.size,
    uploadedAt: new Date().toISOString(),
    status: 'queued',
    stage: 'queued',
    progress: 0
  })

  return toResponse(jobs.get(jobId))
}

export async function getMockAnalysisStatus(jobId) {
  await wait(180)
  const job = jobs.get(jobId)
  if (!job) throw new Error('분석 작업을 찾을 수 없습니다.')
  return toResponse(job)
}

export async function cancelMockAnalysis(jobId) {
  await wait(220)
  const job = jobs.get(jobId)
  if (!job) throw new Error('분석 작업을 찾을 수 없습니다.')

  job.status = 'cancelled'
  return toResponse(job)
}

export async function getMockAnalysisResult(jobId) {
  await wait(220)
  const job = jobs.get(jobId)
  if (!job) throw new Error('분석 작업을 찾을 수 없습니다.')

  const status = toResponse(job).status
  if (status !== 'completed') throw new Error('분석이 아직 완료되지 않았습니다.')

  return {
    job_id: jobId,
    status: 'completed',
    result: {
      label: '보이스피싱 의심',
      score: 91,
      risk_level: 5,
      risk_level_label: '매우 높음',
      summary: {
        title: '보이스피싱 의심',
        description: '분석된 통화 내용에서 보이스피싱으로 판단되는 발언과 패턴이 다수 탐지되었습니다.'
      },
      segments: [
        { start_time: '00:01:24', text: '저는 서울중앙지검 수사관 김○○입니다.', reason: '수사기관 사칭 표현' },
        { start_time: '00:02:47', text: '지금 고객님 명의가 범죄에 연루되어 있습니다.', reason: '범죄 연루로 불안 조성' },
        { start_time: '00:04:15', text: '안전을 위해 계좌에 있는 돈을 확인해야 합니다.', reason: '자금 이체 유도 의심' }
      ],
      advice: [
        '어떤 이유로도 현금 이체나 계좌이체를 하지 마세요.',
        '의심되는 경우 말을 잇지 말고 즉시 전화를 끊으세요.',
        '공식 기관의 대표번호로 직접 연락해 사실 여부를 확인하세요.'
      ],
      disclaimer: 'AI 분석 결과는 법적 확정 판정이 아니며 참고용으로 활용해 주세요.'
    }
  }
}

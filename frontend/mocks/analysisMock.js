function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

export async function createMockAnalysis(file) {
  await wait(350)
  return {
    job_id: `mock_job_${Date.now()}`,
    status: 'queued',
    stage: 'queued',
    file_name: file.name
  }
}

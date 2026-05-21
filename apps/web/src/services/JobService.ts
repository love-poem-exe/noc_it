import { requestJson } from './ApiClient'

type JobStatus = {
  jobId: string
  state: string
  ready: boolean
  result?: any
}

const buildWsUrl = (jobId: string) => {
  const envUrl = (import.meta as any).env?.VITE_WS_BASE_URL as string | undefined
  if (envUrl) {
    const base = envUrl.endsWith('/') ? envUrl.slice(0, -1) : envUrl
    return `${base}/ws/jobs/${encodeURIComponent(jobId)}`
  }
  const protocol = window?.location?.protocol === 'https:' ? 'wss://' : 'ws://'
  const host = window?.location?.host || 'localhost'
  return `${protocol}${host}/ws/jobs/${encodeURIComponent(jobId)}`
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForJobWs = (jobId: string, timeoutMs: number): Promise<JobStatus> => {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(buildWsUrl(jobId))
    let timer: number | undefined

    if (timeoutMs) {
      timer = window.setTimeout(() => {
        ws.close()
        reject(new Error(`Job ${jobId} timeout after ${timeoutMs}ms`))
      }, timeoutMs)
    }

    ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(String(ev.data))
        const payload = msg.payload || msg
        if (payload?.jobId !== jobId) return
        if (payload?.ready) {
          if (timer) window.clearTimeout(timer)
          ws.close()
          resolve(payload)
        }
      } catch (err) {
        if (timer) window.clearTimeout(timer)
        ws.close()
        reject(err)
      }
    })

    ws.addEventListener('error', () => {
      if (timer) window.clearTimeout(timer)
      ws.close()
      reject(new Error(`Job ${jobId} websocket error`))
    })
  })
}

const waitForJobPoll = async (jobId: string, timeoutMs: number) => {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const status = await requestJson(`/api/jobs/${encodeURIComponent(jobId)}`)
    if (status?.ready) return status as JobStatus
    await sleep(1000)
  }
  throw new Error(`Job ${jobId} timeout after ${timeoutMs}ms`)
}

const waitForJob = async (jobId: string, timeoutMs: number) => {
  try {
    return await waitForJobWs(jobId, timeoutMs)
  } catch {
    return await waitForJobPoll(jobId, timeoutMs)
  }
}

export { waitForJob }
export type { JobStatus }

type RequestOptions = {
  method?: string
  body?: any
  timeoutMs?: number
  headers?: Record<string, string>
}

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || ''

const buildUrl = (path: string) => {
  if (!path) return API_BASE_URL
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${cleanPath}`
}

const withTimeout = (timeoutMs?: number) => {
  if (!timeoutMs) return { controller: undefined as AbortController | undefined, timer: undefined as number | undefined }
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  return { controller, timer }
}

const normalizeError = async (res: Response) => {
  const text = await res.text()
  const detail = text ? `: ${text}` : ''
  return new Error(`HTTP ${res.status} ${res.statusText}${detail}`)
}

const requestRaw = async (path: string, options: RequestOptions = {}) => {
  const { method = 'GET', body, timeoutMs, headers = {} } = options
  const { controller, timer } = withTimeout(timeoutMs)

  try {
    const res = await fetch(buildUrl(path), {
      method,
      headers,
      body,
      credentials: 'include',
      signal: controller?.signal
    })

    if (!res.ok) {
      throw await normalizeError(res)
    }

    return res
  } finally {
    if (timer) window.clearTimeout(timer)
  }
}

const requestJson = async (path: string, options: RequestOptions = {}) => {
  const { body, headers = {}, ...rest } = options
  const res = await requestRaw(path, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    body: body !== undefined ? JSON.stringify(body) : undefined
  })

  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

const requestText = async (path: string, options: RequestOptions = {}) => {
  const res = await requestRaw(path, options)
  return res.text()
}

const requestForm = async (path: string, form: FormData, options: RequestOptions = {}) => {
  return requestRaw(path, {
    ...options,
    body: form
  })
}

export { requestJson, requestText, requestForm }

// Centralised API client for DeepTrace AI. Configure the backend origin with VITE_API_BASE_URL
// (see .env.example). No other file should build backend URLs by hand.

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
export const API_BASE = RAW_BASE.replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, { status = 0, kind = 'http' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind // 'network' | 'http' | 'parse'
  }
}

const STATUS_HINTS = {
  400: 'The uploaded file is empty.',
  413: 'The file is too large for the server limit.',
  415: 'This file is not a supported image (JPEG, PNG or WebP).',
  422: 'The image could not be read; it may be corrupted.',
  500: 'The server hit an unexpected error. Please try again.',
}

/** Build an absolute URL for a backend-relative path such as /api/v1/analyses/<id>/report. */
export const absoluteUrl = (path) => (path ? `${API_BASE}${path}` : '')

async function request(path, options) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new ApiError(
      `Cannot reach the DeepTrace backend at ${API_BASE}. Start it with "uvicorn app.main:app --reload" and check CORS settings.`,
      { kind: 'network' },
    )
  }

  let body = null
  const isJson = (response.headers.get('content-type') || '').includes('application/json')
  if (isJson) {
    try {
      body = await response.json()
    } catch {
      throw new ApiError('The server returned an unreadable response.', { status: response.status, kind: 'parse' })
    }
  }

  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : null
    throw new ApiError(detail || STATUS_HINTS[response.status] || `Request failed (HTTP ${response.status}).`, {
      status: response.status,
    })
  }
  return body
}

export const getHealth = () => request('/api/v1/health')

export const analyzeImage = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/api/v1/analyze', { method: 'POST', body: form })
}

export const listAnalyses = (limit = 50, offset = 0) =>
  request(`/api/v1/analyses?limit=${limit}&offset=${offset}`)

export const getAnalysis = (id) => request(`/api/v1/analyses/${encodeURIComponent(id)}`)

export const deleteAnalysis = (id) =>
  request(`/api/v1/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' })

export const reportUrl = (id) => absoluteUrl(`/api/v1/analyses/${encodeURIComponent(id)}/report`)

/** Download the PDF through fetch so failures (404 etc.) show a message instead of a blank tab. */
export async function downloadReport(id) {
  let response
  try {
    response = await fetch(reportUrl(id))
  } catch {
    throw new ApiError('Cannot reach the backend to download the report.', { kind: 'network' })
  }
  if (!response.ok) {
    throw new ApiError(response.status === 404 ? 'The report is no longer available.' : 'Report download failed.', {
      status: response.status,
    })
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `deeptrace_report_${id}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

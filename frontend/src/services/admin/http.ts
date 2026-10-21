import { notifySessionExpired } from '../shared/sessionEvents.ts'

export const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export const ADMIN_BASE = `${API_BASE_URL}/v1/admin`

export const STUDENT_BASE = `${API_BASE_URL}/v1/students`

export const FACULTY_BASE = `${API_BASE_URL}/v1/faculty`

export class AdminApiError extends Error {
  readonly status: number
  readonly details: unknown
  readonly code: string | null

  constructor(status: number, message: string, details: unknown = undefined, code: string | null = null) {
    super(message)
    this.name = 'AdminApiError'
    this.status = status
    this.details = details
    this.code = code
  }
}

export async function readErrorDetails(response: Response): Promise<{ details: unknown; code: string | null }> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return { details: undefined, code: null }
  try {
    const body = await response.json()
    let code: string | null = null
    if (typeof body === 'object' && body !== null) {
      const envelope = (body as Record<string, unknown>).error
      if (typeof envelope === 'object' && envelope !== null) {
        const c = (envelope as Record<string, unknown>).code
        if (typeof c === 'string') code = c
      }
    }
    return { details: body, code }
  } catch {
    return { details: undefined, code: null }
  }
}

export function formatErrorMessage(status: number, details: unknown, code: string | null): string {
  if (typeof details === 'object' && details !== null) {
    const detail = (details as Record<string, unknown>).detail
    if (typeof detail === 'string' && detail.length > 0) return detail
    const envelope = (details as Record<string, unknown>).error
    if (typeof envelope === 'object' && envelope !== null) {
      const msg = (envelope as Record<string, unknown>).message
      if (typeof msg === 'string' && msg.length > 0) return msg
    }
  }
  if (code) return `Request failed (${code})`
  return `Request failed with HTTP ${status}`
}

export async function requestJson<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  endpoint: string,
  accessToken: string,
  body?: unknown,
): Promise<T> {
  let response: Response
  try {
    const headers: Record<string, string> = { Authorization: `Bearer ${accessToken}` }
    if (body !== undefined && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }
    response = await fetch(endpoint, {
      method,
      headers,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    })
  } catch {
    throw new AdminApiError(
      0,
      'Could not reach the backend. Please make sure the server is running.',
      undefined,
      'NETWORK_ERROR',
    )
  }
  if (!response.ok) {
    const { details, code } = await readErrorDetails(response)
    // Phase 6.15.4 — global session-expiry handling: every admin/student
    // request sends a bearer token, so a 401 means the token is no longer
    // accepted (TOKEN_EXPIRED / INVALID_TOKEN / USER_NOT_FOUND).
    // Phase 6.15.7 — the notification names the token used, so a late 401 from
    // a replaced session cannot clear a newer one.
    if (response.status === 401) notifySessionExpired(accessToken)
    throw new AdminApiError(response.status, formatErrorMessage(response.status, details, code), details, code)
  }
  return (await response.json()) as T
}

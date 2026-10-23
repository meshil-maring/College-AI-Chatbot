import { notifySessionExpired } from '../shared/sessionEvents.ts'
import type { StudentIdentityProfile, StudentNoticeList, StudentResourceList } from '../../types/student.ts'

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/students/me`

export class StudentApiError extends Error {
  readonly status: number
  readonly details: unknown
  readonly code: string | null
  constructor(status: number, message: string, details?: unknown, code: string | null = null) {
    super(message)
    this.name = 'StudentApiError'
    this.status = status
    this.details = details
    this.code = code
  }
}
async function getJson<T>(endpoint: string, accessToken: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(endpoint, { method: 'GET', headers: { Authorization: `Bearer ${accessToken}` } })
  } catch {
    throw new StudentApiError(
      0,
      'Could not reach the backend. Please make sure the server is running.',
      undefined,
      'NETWORK_ERROR',
    )
  }
  if (!response.ok) {
    let details: unknown
    if (response.headers.get('content-type')?.includes('application/json')) {
      try {
        details = await response.json()
      } catch {
        details = undefined
      }
    }
    let message = `Request failed with HTTP ${response.status}`
    let code: string | null = null
    if (typeof details === 'object' && details !== null) {
      const body = details as Record<string, unknown>
      if (typeof body.detail === 'string' && body.detail) message = body.detail
      if (typeof body.error === 'object' && body.error !== null) {
        const error = body.error as Record<string, unknown>
        if (typeof error.code === 'string') code = error.code
        if (typeof error.message === 'string' && error.message) message = error.message
        else if (code && message.startsWith('Request failed with HTTP')) message = `Request failed (${code})`
      }
    }
    if (response.status === 401) notifySessionExpired(accessToken)
    throw new StudentApiError(response.status, message, details, code)
  }
  return (await response.json()) as T
}
export function getMyProfile(accessToken: string): Promise<StudentIdentityProfile> {
  return getJson(`${BASE}/profile`, accessToken)
}
export function getMyNotices(accessToken: string, limit = 5): Promise<StudentNoticeList> {
  return getJson(`${BASE}/notices?limit=${encodeURIComponent(String(limit))}`, accessToken)
}
export function getMyResources(accessToken: string, limit = 6): Promise<StudentResourceList> {
  return getJson(`${BASE}/resources?limit=${encodeURIComponent(String(limit))}`, accessToken)
}

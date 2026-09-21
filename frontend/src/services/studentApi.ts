/**
 * Phase 6.16 — Student self-service API client.
 *
 * The only HTTP boundary the student experience dashboard uses. It talks
 * exclusively to the EXISTING authenticated student endpoints (all of them
 * resolve the student's identity and tenant server-side from the JWT):
 *
 *   GET /api/v1/students/me/academic-profile
 *   GET /api/v1/students/me/attendance/summary
 *   GET /api/v1/students/me/results/summary
 *   GET /api/v1/students/me/test-results/summary
 *   GET /api/v1/students/me/notices
 *   GET /api/v1/students/me/resources
 *
 * Boundaries:
 * - Every request is a read; this module exposes no mutation functions, so the
 *   dashboard cannot mark attendance, edit results, or publish content.
 * - The access token is opaque: sent only as `Authorization: Bearer <token>`,
 *   never in a URL/body, never rendered.
 * - Phase 6.15.7 session lifecycle is reused verbatim: a 401 raises the
 *   existing global session-expiry notification (naming the token used), which
 *   AuthProvider turns into a sign-out. No second session mechanism exists.
 * - Failures are typed (`StudentApiError`) so the UI can distinguish
 *   loading / empty / error per section. Backend error text is user-safe by
 *   contract (the backend never returns stack traces, SQL, or internal ids).
 *
 * Uses the browser-native `fetch` API (no HTTP library is installed), matching
 * `services/api.ts` and `services/adminApi.ts`.
 */

import { notifySessionExpired } from './sessionEvents.ts'
import type {
  StudentAcademicProfile,
  StudentNoticeList,
  StudentOwnAttendance,
  StudentOwnResults,
  StudentOwnTestResults,
  StudentResourceList,
} from '../types/student.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const STUDENT_BASE = `${API_BASE_URL}/v1/students/me`

/** Error raised for a failed student request. Never carries backend internals. */
export class StudentApiError extends Error {
  /** HTTP status, or 0 when the request never produced a response. */
  readonly status: number
  readonly details: unknown
  /** Stable backend error code (`FORBIDDEN`, `STUDENT_NOT_APPROVED`, …). */
  readonly code: string | null

  constructor(status: number, message: string, details: unknown = undefined, code: string | null = null) {
    super(message)
    this.name = 'StudentApiError'
    this.status = status
    this.details = details
    this.code = code
  }
}

async function readErrorDetails(response: Response): Promise<{ details: unknown; code: string | null }> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return { details: undefined, code: null }
  try {
    const body = await response.json()
    let code: string | null = null
    if (typeof body === 'object' && body !== null) {
      const envelope = (body as Record<string, unknown>).error
      if (typeof envelope === 'object' && envelope !== null) {
        const candidate = (envelope as Record<string, unknown>).code
        if (typeof candidate === 'string') code = candidate
      }
    }
    return { details: body, code }
  } catch {
    return { details: undefined, code: null }
  }
}

function formatErrorMessage(status: number, details: unknown, code: string | null): string {
  if (typeof details === 'object' && details !== null) {
    const detail = (details as Record<string, unknown>).detail
    if (typeof detail === 'string' && detail.length > 0) return detail
    const envelope = (details as Record<string, unknown>).error
    if (typeof envelope === 'object' && envelope !== null) {
      const message = (envelope as Record<string, unknown>).message
      if (typeof message === 'string' && message.length > 0) return message
    }
  }
  if (code) return `Request failed (${code})`
  return `Request failed with HTTP ${status}`
}

async function getJson<T>(endpoint: string, accessToken: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(endpoint, {
      method: 'GET',
      headers: { Authorization: `Bearer ${accessToken}` },
    })
  } catch {
    throw new StudentApiError(
      0,
      'Could not reach the backend. Please make sure the server is running.',
      undefined,
      'NETWORK_ERROR',
    )
  }
  if (!response.ok) {
    const { details, code } = await readErrorDetails(response)
    if (response.status === 401) notifySessionExpired(accessToken)
    throw new StudentApiError(
      response.status,
      formatErrorMessage(response.status, details, code),
      details,
      code,
    )
  }
  return (await response.json()) as T
}

// ============================================================================
// Read-only student endpoints
// ============================================================================

/** GET /api/v1/students/me/academic-profile — identity + academic context. */
export async function getMyAcademicProfile(accessToken: string): Promise<StudentAcademicProfile> {
  return getJson<StudentAcademicProfile>(`${STUDENT_BASE}/academic-profile`, accessToken)
}

/** GET /api/v1/students/me/attendance/summary — own attendance summary + rows. */
export async function getMyAttendanceSummary(accessToken: string): Promise<StudentOwnAttendance> {
  return getJson<StudentOwnAttendance>(`${STUDENT_BASE}/attendance/summary`, accessToken)
}

/** GET /api/v1/students/me/results/summary — own published academic results. */
export async function getMyResultsSummary(accessToken: string): Promise<StudentOwnResults> {
  return getJson<StudentOwnResults>(`${STUDENT_BASE}/results/summary`, accessToken)
}

/** GET /api/v1/students/me/test-results/summary — own published test scores. */
export async function getMyTestResultsSummary(accessToken: string): Promise<StudentOwnTestResults> {
  return getJson<StudentOwnTestResults>(`${STUDENT_BASE}/test-results/summary`, accessToken)
}

/** GET /api/v1/students/me/notices — own institution's published notices. */
export async function getMyNotices(accessToken: string, limit = 5): Promise<StudentNoticeList> {
  return getJson<StudentNoticeList>(
    `${STUDENT_BASE}/notices?limit=${encodeURIComponent(String(limit))}`,
    accessToken,
  )
}

/** GET /api/v1/students/me/resources — own institution's published resources. */
export async function getMyResources(accessToken: string, limit = 6): Promise<StudentResourceList> {
  return getJson<StudentResourceList>(
    `${STUDENT_BASE}/resources?limit=${encodeURIComponent(String(limit))}`,
    accessToken,
  )
}


/**
 * Phase Admin-4 — Admin API client.
 *
 * Uses the browser-native `fetch` API (no HTTP library installed).
 * Every request sends the Supabase JWT as `Authorization: Bearer <token>`.
 * The backend is authoritative: admin endpoints require the `admin` role.
 */

import type {
  AdminIdentity,
  AttendanceCreate,
  AttendanceRecord,
  AttendanceUpdate,
  AuditLogEntry,
  DashboardSummary,
  DocumentWithVersions,
  Faq,
  FaqCreate,
  FaqUpdate,
  KnowledgeSource,
  KnowledgeSourceCreate,
  KnowledgeSourceUpdate,
  Notice,
  NoticeCreate,
  NoticeUpdate,
  ResultCreate,
  ResultUpdate,
  Student,
  StudentCreate,
  StudentProfile,
  StudentResult,
  StudentUpdate,
  TestResult,
  TestResultCreate,
  TestResultUpdate,
} from '../types/admin.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const ADMIN_BASE = `${API_BASE_URL}/v1/admin`
const STUDENT_BASE = `${API_BASE_URL}/v1/students`

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

async function readErrorDetails(response: Response): Promise<{ details: unknown; code: string | null }> {
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

function formatErrorMessage(status: number, details: unknown, code: string | null): string {
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

async function requestJson<T>(
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
    throw new AdminApiError(0, 'Could not reach the backend. Please make sure the server is running.', undefined, 'NETWORK_ERROR')
  }
  if (!response.ok) {
    const { details, code } = await readErrorDetails(response)
    throw new AdminApiError(response.status, formatErrorMessage(response.status, details, code), details, code)
  }
  return (await response.json()) as T
}

// ============================================================================
// Admin identity + Dashboard
// ============================================================================

export async function getAdminIdentity(accessToken: string): Promise<AdminIdentity> {
  return requestJson<AdminIdentity>('GET', `${ADMIN_BASE}/me`, accessToken)
}

export async function getDashboardSummary(accessToken: string, institutionId?: string): Promise<DashboardSummary> {
  const params = institutionId ? `?institution_id=${encodeURIComponent(institutionId)}` : ''
  return requestJson<DashboardSummary>('GET', `${ADMIN_BASE}/dashboard${params}`, accessToken)
}

// ============================================================================
// Knowledge sources + Documents
// ============================================================================

export async function listKnowledgeSources(accessToken: string, institutionId: string): Promise<KnowledgeSource[]> {
  return requestJson<KnowledgeSource[]>('GET', `${ADMIN_BASE}/knowledge-sources?institution_id=${encodeURIComponent(institutionId)}`, accessToken)
}

export async function createKnowledgeSource(accessToken: string, payload: KnowledgeSourceCreate): Promise<KnowledgeSource> {
  return requestJson<KnowledgeSource>('POST', `${ADMIN_BASE}/knowledge-sources`, accessToken, payload)
}

export async function updateKnowledgeSource(accessToken: string, id: string, payload: KnowledgeSourceUpdate): Promise<KnowledgeSource> {
  return requestJson<KnowledgeSource>('PATCH', `${ADMIN_BASE}/knowledge-sources/${id}`, accessToken, payload)
}

export async function listDocuments(accessToken: string, knowledgeSourceId: string): Promise<DocumentWithVersions[]> {
  return requestJson<DocumentWithVersions[]>('GET', `${ADMIN_BASE}/knowledge-sources/${knowledgeSourceId}/documents`, accessToken)
}

export async function uploadDocument(accessToken: string, knowledgeSourceId: string, file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('knowledge_source_id', knowledgeSourceId)
  return requestJson<unknown>('POST', `${ADMIN_BASE}/documents`, accessToken, formData)
}

export async function deleteDocument(accessToken: string, documentId: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/documents/${documentId}`, accessToken)
}

// ============================================================================
// FAQs
// ============================================================================

export async function listFaqs(accessToken: string, institutionId?: string): Promise<Faq[]> {
  const params = institutionId ? `?institution_id=${encodeURIComponent(institutionId)}` : ''
  return requestJson<Faq[]>('GET', `${ADMIN_BASE}/faqs${params}`, accessToken)
}

export async function createFaq(accessToken: string, payload: FaqCreate): Promise<Faq> {
  return requestJson<Faq>('POST', `${ADMIN_BASE}/faqs`, accessToken, payload)
}

export async function updateFaq(accessToken: string, id: string, payload: FaqUpdate): Promise<Faq> {
  return requestJson<Faq>('PATCH', `${ADMIN_BASE}/faqs/${id}`, accessToken, payload)
}

export async function deleteFaq(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/faqs/${id}`, accessToken)
}

// ============================================================================
// Notices
// ============================================================================

export async function listNotices(accessToken: string, institutionId?: string): Promise<Notice[]> {
  const params = institutionId ? `?institution_id=${encodeURIComponent(institutionId)}` : ''
  return requestJson<Notice[]>('GET', `${ADMIN_BASE}/notices${params}`, accessToken)
}

export async function createNotice(accessToken: string, payload: NoticeCreate): Promise<Notice> {
  return requestJson<Notice>('POST', `${ADMIN_BASE}/notices`, accessToken, payload)
}

export async function updateNotice(accessToken: string, id: string, payload: NoticeUpdate): Promise<Notice> {
  return requestJson<Notice>('PATCH', `${ADMIN_BASE}/notices/${id}`, accessToken, payload)
}

export async function deleteNotice(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/notices/${id}`, accessToken)
}

// ============================================================================
// Students + Results + Test Results + Attendance
// ============================================================================

export async function listStudents(accessToken: string, institutionId: string): Promise<Student[]> {
  return requestJson<Student[]>('GET', `${ADMIN_BASE}/students?institution_id=${encodeURIComponent(institutionId)}`, accessToken)
}

export async function createStudent(accessToken: string, payload: StudentCreate): Promise<Student> {
  return requestJson<Student>('POST', `${ADMIN_BASE}/students`, accessToken, payload)
}

export async function updateStudent(accessToken: string, id: string, payload: StudentUpdate): Promise<Student> {
  return requestJson<Student>('PATCH', `${ADMIN_BASE}/students/${id}`, accessToken, payload)
}

export async function deleteStudent(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/students/${id}`, accessToken)
}

export async function listStudentResults(accessToken: string, studentId: string): Promise<StudentResult[]> {
  return requestJson<StudentResult[]>('GET', `${ADMIN_BASE}/students/${studentId}/results`, accessToken)
}

export async function createResult(accessToken: string, payload: ResultCreate): Promise<StudentResult> {
  return requestJson<StudentResult>('POST', `${ADMIN_BASE}/results`, accessToken, payload)
}

export async function updateResult(accessToken: string, id: string, payload: ResultUpdate): Promise<StudentResult> {
  return requestJson<StudentResult>('PATCH', `${ADMIN_BASE}/results/${id}`, accessToken, payload)
}

export async function deleteResult(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/results/${id}`, accessToken)
}

export async function uploadResultsCsv(accessToken: string, file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  return requestJson<unknown>('POST', `${ADMIN_BASE}/results/csv`, accessToken, formData)
}

export async function listTestResults(accessToken: string, studentId: string): Promise<TestResult[]> {
  return requestJson<TestResult[]>('GET', `${ADMIN_BASE}/students/${studentId}/test-results`, accessToken)
}

export async function createTestResult(accessToken: string, payload: TestResultCreate): Promise<TestResult> {
  return requestJson<TestResult>('POST', `${ADMIN_BASE}/test-results`, accessToken, payload)
}

export async function updateTestResult(accessToken: string, id: string, payload: TestResultUpdate): Promise<TestResult> {
  return requestJson<TestResult>('PATCH', `${ADMIN_BASE}/test-results/${id}`, accessToken, payload)
}

export async function deleteTestResult(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/test-results/${id}`, accessToken)
}

export async function listAttendance(accessToken: string, studentId: string): Promise<AttendanceRecord[]> {
  return requestJson<AttendanceRecord[]>('GET', `${ADMIN_BASE}/students/${studentId}/attendance`, accessToken)
}

export async function createAttendance(accessToken: string, payload: AttendanceCreate): Promise<AttendanceRecord> {
  return requestJson<AttendanceRecord>('POST', `${ADMIN_BASE}/attendance`, accessToken, payload)
}

export async function updateAttendance(accessToken: string, id: string, payload: AttendanceUpdate): Promise<AttendanceRecord> {
  return requestJson<AttendanceRecord>('PATCH', `${ADMIN_BASE}/attendance/${id}`, accessToken, payload)
}

export async function deleteAttendance(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/attendance/${id}`, accessToken)
}

// ============================================================================
// Audit logs
// ============================================================================

export async function listAuditLogs(accessToken: string, limit = 50): Promise<AuditLogEntry[]> {
  return requestJson<AuditLogEntry[]>('GET', `${ADMIN_BASE}/audit-logs?limit=${limit}`, accessToken)
}

// ============================================================================
// Student self-service ("me" endpoints)
// ============================================================================

export async function getMyProfile(accessToken: string): Promise<StudentProfile> {
  return requestJson<StudentProfile>('GET', `${STUDENT_BASE}/me/profile`, accessToken)
}

export async function getMyResults(accessToken: string): Promise<StudentResult[]> {
  return requestJson<StudentResult[]>('GET', `${STUDENT_BASE}/me/results`, accessToken)
}

export async function getMyTestResults(accessToken: string): Promise<TestResult[]> {
  return requestJson<TestResult[]>('GET', `${STUDENT_BASE}/me/test-results`, accessToken)
}

export async function getMyAttendance(accessToken: string): Promise<AttendanceRecord[]> {
  return requestJson<AttendanceRecord[]>('GET', `${STUDENT_BASE}/me/attendance`, accessToken)
}

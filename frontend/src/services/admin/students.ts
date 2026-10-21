import type {
  AttendanceCreate,
  AttendanceRecord,
  AttendanceUpdate,
  CsvUploadResult,
  PendingStudent,
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
} from '../../types/admin.ts'
import { ADMIN_BASE, STUDENT_BASE, requestJson } from './http.ts'
// ============================================================================
// Students + Results + Test Results + Attendance
// ============================================================================

export async function listStudents(
  accessToken: string,
  institutionId: string,
  pagination?: { limit: number; offset: number },
): Promise<Student[]> {
  const suffix = pagination ? `&limit=${pagination.limit}&offset=${pagination.offset}` : ''
  return requestJson<Student[]>(
    'GET',
    `${ADMIN_BASE}/students?institution_id=${encodeURIComponent(institutionId)}${suffix}`,
    accessToken,
  )
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

/**
 * Phase 6.19 — verified defect fix: the backend route is
 * `POST /admin/results/csv-upload` (NOT `/results/csv`), it REQUIRES the
 * `institution_id` multipart Form field, and the response is the backend
 * `CsvUploadResult` contract (`{total_rows, inserted_count, failed_count,
 * row_errors}`), NOT the `{uploaded, errors}` shape the client previously
 * assumed. The institution value is only a server-validated filter: the
 * backend re-scopes it against the authenticated JWT tenant
 * (scope_tenant), so a foreign value fails closed with 403 TENANT_MISMATCH.
 */
export async function uploadResultsCsv(
  accessToken: string,
  file: File,
  institutionId: string,
): Promise<CsvUploadResult> {
  const formData = new FormData()
  formData.append('institution_id', institutionId)
  formData.append('file', file)
  return requestJson<CsvUploadResult>('POST', `${ADMIN_BASE}/results/csv-upload`, accessToken, formData)
}

export async function listTestResults(accessToken: string, studentId: string): Promise<TestResult[]> {
  return requestJson<TestResult[]>('GET', `${ADMIN_BASE}/students/${studentId}/test-results`, accessToken)
}

export async function createTestResult(accessToken: string, payload: TestResultCreate): Promise<TestResult> {
  return requestJson<TestResult>('POST', `${ADMIN_BASE}/test-results`, accessToken, payload)
}

export async function updateTestResult(
  accessToken: string,
  id: string,
  payload: TestResultUpdate,
): Promise<TestResult> {
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

export async function updateAttendance(
  accessToken: string,
  id: string,
  payload: AttendanceUpdate,
): Promise<AttendanceRecord> {
  return requestJson<AttendanceRecord>('PATCH', `${ADMIN_BASE}/attendance/${id}`, accessToken, payload)
}

export async function deleteAttendance(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/attendance/${id}`, accessToken)
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

// ============================================================================
// Student approval queue (Phase 6.4 backend contract; Phase 6.18 Staff UI)
// ============================================================================
// These endpoints are the ONLY /admin/* surface the backend authorizes for
// the staff role (`require_roles("admin", "staff")` with the tenant-scoped
// `_approval_scope`). Tenant-bound staff always receive their OWN
// institution's queue server-side; this client never sends an
// `institution_id` (the backend resolves the tenant from the authenticated
// JWT). Approve/reject bodies accept NO fields, so no decision target can
// be spoofed from the client.

export async function listPendingStudents(accessToken: string, limit = 100, offset = 0): Promise<PendingStudent[]> {
  const params = `?limit=${limit}&offset=${offset}`
  return requestJson<PendingStudent[]>('GET', `${ADMIN_BASE}/students/pending${params}`, accessToken)
}

export async function approvePendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson<PendingStudent>(
    'POST',
    `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/approve`,
    accessToken,
  )
}

export async function rejectPendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson<PendingStudent>(
    'POST',
    `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/reject`,
    accessToken,
  )
}

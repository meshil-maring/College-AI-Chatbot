import { AdminApiError } from './adminApi.ts'

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/faculty/attendance`

async function request<T>(endpoint: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${endpoint}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(init.headers ?? {}) },
  })
  if (!response.ok) {
    let body: unknown
    try { body = await response.json() } catch { body = undefined }
    const envelope = typeof body === 'object' && body !== null ? (body as { error?: { message?: string; code?: string } }).error : undefined
    throw new AdminApiError(response.status, envelope?.message ?? 'Attendance request failed', body, envelope?.code ?? null)
  }
  return response.json() as Promise<T>
}

export interface FacultyAttendanceRosterRow {
  roster_id: string
  register_number: string
  university_roll_number: string | null
  student_name: string
  email: string | null
  address?: string | null
  roster_status: 'UNREGISTERED' | 'PENDING_APPROVAL' | 'ACTIVE' | 'INACTIVE'
  linked_student_id: string | null
  imported_summary?: Record<string, unknown> | null
  record_count?: number
  present?: number
  absent?: number
  attendance_percentage?: number | null
  reconciliation_state?: 'NONE' | 'PENDING' | 'LINKED' | 'CONFLICT'
}

export interface FacultyAttendanceAssignment {
  assignment_id: string
  assigned_at: string
  can_manage?: boolean
  section_id: string
  semester_id: string
  academic_year_id: string
  section: AttendanceSection
}

export interface AttendanceSection {
  section_id: string; name: string; code: string; semester_id?: string
  department_id?: string; program_id?: string; academic_year_id?: string; course_id?: string
  department?: { department_id: string; name: string }
  program?: { program_id: string; name: string }
  academic_year?: { academic_year_id: string; name: string }
  semester?: { semester_id: string; name: string }
  course: { name: string; code: string; course_id?: string }
  can_manage?: boolean
}

export interface AttendanceOverview {
  total_students: number; session_count: number; present: number; absent: number
  average_attendance: number | null; low_attendance_count: number; monitoring_threshold: number
  trend: Array<{ date: string; record_count: number; attendance_percentage: number | null; present: number; absent: number }>
}
export interface AttendanceSession {
  session_id: string | null; session_date: string; conducted_by?: string
  record_count: number; present: number; absent: number; attendance_percentage: number | null
}
export interface AttendanceProfile {
  student: FacultyAttendanceRosterRow; section: AttendanceSection; total: number
  history: Array<{ record_id: string; session_date: string; status: string }>
}
export interface AttendanceImport {
  import_id: string; original_filename: string; uploaded_by: string; created_at: string
  status: string; summary: Record<string, number>
}

export interface FacultyAttendanceImportReview {
  import_id: string
  status: string
  summary: Record<string, number>
  rows: Array<{ row_number: number; normalized_data: Record<string, string>; validation_status: string; errors: string[]; warnings?: string[] }>
}

export const getFacultyAttendanceRoster = (token: string, sectionId: string, offset = 0) =>
  request<FacultyAttendanceRosterRow[]>(`/sections/${encodeURIComponent(sectionId)}/roster?limit=500&offset=${offset}`, token)

export const getFacultyAttendanceAssignments = async (token: string): Promise<FacultyAttendanceAssignment[]> => {
  const sections = await request<AttendanceSection[]>('/resources', token)
  return sections.map((section) => ({ assignment_id: section.section_id, assigned_at: '',
    section_id: section.section_id, semester_id: section.semester_id ?? '', academic_year_id: section.academic_year_id ?? '',
    section, can_manage: section.can_manage ?? false }))
}

export const getFacultyAttendanceOverview = (token: string, sectionId: string) =>
  request<AttendanceOverview>(`/sections/${encodeURIComponent(sectionId)}/overview`, token)

export const getFacultyAttendanceStudents = (token: string, sectionId: string, query: URLSearchParams) =>
  request<{ items: FacultyAttendanceRosterRow[]; total: number }>(`/sections/${encodeURIComponent(sectionId)}/students?${query}`, token)

export const getFacultyAttendanceProfile = (token: string, rosterId: string, offset = 0) =>
  request<AttendanceProfile>(`/roster/${encodeURIComponent(rosterId)}/profile?offset=${offset}`, token)

export const getFacultyAttendanceSessions = (token: string, sectionId: string, offset = 0) =>
  request<{ items: AttendanceSession[]; total: number }>(`/sections/${encodeURIComponent(sectionId)}/sessions?offset=${offset}`, token)

export const getFacultyAttendanceImports = (token: string, sectionId: string, offset = 0) =>
  request<AttendanceImport[]>(`/sections/${encodeURIComponent(sectionId)}/imports?offset=${offset}`, token)

export const correctFacultyAttendanceImportRow = (token: string, importId: string, row: number, data: Record<string, string>) =>
  request<FacultyAttendanceImportReview>(`/imports/${encodeURIComponent(importId)}/rows/${row}`, token, { method: 'PATCH', body: JSON.stringify({ data }) })

export const addFacultyAttendanceStudent = (token: string, sectionId: string, data: { register_number: string; university_roll_number?: string; student_name: string; email?: string }) =>
  request<FacultyAttendanceRosterRow>(`/sections/${encodeURIComponent(sectionId)}/roster`, token, { method: 'POST', body: JSON.stringify(data) })

export async function uploadFacultyAttendance(
  token: string,
  sectionId: string,
  semesterId: string,
  file: File,
  aiConfirmed = false,
) {
  const body = new FormData()
  body.append('semester_id', semesterId)
  body.append('ai_confirmed', String(aiConfirmed))
  body.append('file', file)
  return request<{ import_id: string; summary: Record<string, number>; rows: FacultyAttendanceImportReview['rows'] }>(`/sections/${encodeURIComponent(sectionId)}/imports`, token, { method: 'POST', body })
}

export const markFacultyAttendance = (
  token: string,
  sectionId: string,
  sessionDate: string,
  attendance: Record<string, 'present' | 'absent' | 'late' | 'excused'>,
) => request<{ session_id: string; record_count: number }>(
  `/sections/${encodeURIComponent(sectionId)}/mark`,
  token,
  { method: 'POST', body: JSON.stringify({ session_date: sessionDate, attendance }) },
)

export const getFacultyAttendanceImportReview = (token: string, importId: string) =>
  request<FacultyAttendanceImportReview>(`/imports/${encodeURIComponent(importId)}/review`, token)

export const commitFacultyAttendanceImport = (token: string, importId: string) =>
  request<{ imported_rows: number }>(`/imports/${encodeURIComponent(importId)}/commit`, token, { method: 'POST' })

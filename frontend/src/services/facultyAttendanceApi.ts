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
  address: string | null
  roster_status: 'UNREGISTERED' | 'PENDING_APPROVAL' | 'ACTIVE' | 'INACTIVE'
  linked_student_id: string | null
  imported_summary?: Record<string, unknown> | null
}

export interface FacultyAttendanceAssignment {
  assignment_id: string
  assigned_at: string
  section_id: string
  semester_id: string
  academic_year_id: string
  section: { section_id: string; name: string; code: string; semester_id?: string; course: { name: string; code: string } }
}

export interface FacultyAttendanceImportReview {
  import_id: string
  status: string
  summary: Record<string, number>
  rows: Array<{ row_number: number; normalized_data: Record<string, string>; validation_status: string; errors: string[] }>
}

export const getFacultyAttendanceRoster = (token: string, sectionId: string) =>
  request<FacultyAttendanceRosterRow[]>(`/sections/${encodeURIComponent(sectionId)}/roster`, token)

export const getFacultyAttendanceAssignments = (token: string) =>
  request<FacultyAttendanceAssignment[]>('/assignments', token)

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

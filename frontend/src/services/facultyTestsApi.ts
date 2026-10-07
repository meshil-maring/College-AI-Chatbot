import { AdminApiError } from './adminApi.ts'
import { notifySessionExpired } from './sessionEvents.ts'
import type { AttendanceSection } from './facultyAttendanceApi.ts'

const base = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/faculty/tests`

async function request<T>(token: string, path: string, method = 'GET', payload?: unknown): Promise<T> {
  const response = await fetch(`${base}${path}`, { method,
    headers: { Authorization: `Bearer ${token}`, ...(payload instanceof FormData ? {} : { 'Content-Type': 'application/json' }) },
    body: payload === undefined ? undefined : payload instanceof FormData ? payload : JSON.stringify(payload),
  })
  if (!response.ok) {
    const details = await response.json().catch(() => null) as { error?: { message?: string; code?: string }; detail?: string | Array<{ msg?: string; loc?: Array<string | number> }> } | null
    if (response.status === 401) notifySessionExpired(token)
    const validation = Array.isArray(details?.detail) ? details.detail.slice(0, 5).map(issue => `${issue.loc?.slice(1).join(' / ') ?? 'Input'}: ${issue.msg ?? 'Invalid value'}`).join('; ') : details?.detail
    throw new AdminApiError(response.status, details?.error?.message ?? validation ?? 'Assessment request failed', details, details?.error?.code ?? null)
  }
  return response.json() as Promise<T>
}

export type TestStatus = 'DRAFT' | 'SCHEDULED' | 'ONGOING' | 'COMPLETED' | 'PUBLISHED' | 'LOCKED' | 'CANCELLED'
export type MarkStatus = 'present' | 'absent' | 'exempt' | 'not_attempted' | 'missing'
export interface TestInput {
  title: string; test_type: string; description: string | null; max_marks: number; passing_marks: number | null
  scheduled_date: string | null; start_time: string | null; end_time: string | null; duration_minutes: number | null
}
export interface FacultyTest extends TestInput {
  test_id: string; section_id: string; status: TestStatus; marks_state: 'DRAFT' | 'SUBMITTED'; version: number
  created_by: string; created_at: string; updated_at: string; can_manage?: boolean; section?: AttendanceSection
  can_edit_metadata?: boolean
}
export interface MarkRow {
  roster_id: string; register_number: string; university_roll_number: string | null; student_name: string
  roster_status: string; reconciliation_state: string; mark_status: MarkStatus; scored_marks: number | null
  remarks: string | null; percentage: number | null; outcome: string | null
}
export interface MarksDetail { test: FacultyTest; rows: MarkRow[]; review: Record<string, number | null> }
export interface TestList { items: FacultyTest[]; total: number; overview: Record<string, number> }
export interface TestImport {
  import_id: string; test_id: string; original_filename: string; uploaded_by: string; status: string
  updated_at: string; created_at: string; summary: Record<string, number>
  rows: Array<{ row_number: number; raw_data: Record<string, string>; normalized_data: Record<string, string>
    validation_status: string; errors: string[]; warnings: string[] }>
}
export interface TestHistory {
  imports: TestImport[]
  events: Array<{ action: string; actor_user_id: string; performed_at: string; record_data: Record<string, unknown> }>
}

export const getTestResources = (token: string) => request<AttendanceSection[]>(token, '/resources')
export const getTestTypes = (token: string) => request<Array<{ code: string; name: string }>>(token, '/types')
export const getTests = (token: string, section: string, offset = 0) => request<TestList>(token, `/sections/${encodeURIComponent(section)}?offset=${offset}`)
export const getTest = (token: string, id: string) => request<MarksDetail>(token, `/${encodeURIComponent(id)}`)
export const createTest = (token: string, section: string, payload: TestInput) => request<FacultyTest>(token, `/sections/${encodeURIComponent(section)}`, 'POST', payload)
export const updateTest = (token: string, id: string, payload: TestInput & { expected_version: number }) => request<FacultyTest>(token, `/${encodeURIComponent(id)}`, 'PATCH', payload)
export const transitionTest = (token: string, t: FacultyTest, action: string) => request<FacultyTest>(token, `/${encodeURIComponent(t.test_id)}/transition`, 'POST', { expected_version: t.version, action })
export const saveTestMarks = (token: string, t: FacultyTest, rows: Array<Pick<MarkRow, 'roster_id' | 'mark_status' | 'scored_marks' | 'remarks'>>, reason?: string) =>
  request<{ version: number }>(token, `/${encodeURIComponent(t.test_id)}/${reason ? 'corrections' : 'marks'}`, reason ? 'POST' : 'PUT', { expected_version: t.version, rows, ...(reason ? { reason } : {}) })
export const uploadTestMarks = (token: string, id: string, file: File) => {
  const body = new FormData(); body.append('file', file)
  return request<TestImport>(token, `/${encodeURIComponent(id)}/imports`, 'POST', body)
}
export const getTestImport = (token: string, id: string) => request<TestImport>(token, `/imports/${encodeURIComponent(id)}`)
export const correctTestImport = (token: string, item: TestImport, row: number, data: Record<string, string>) =>
  request<TestImport>(token, `/imports/${encodeURIComponent(item.import_id)}/rows/${row}`, 'PATCH', { expected_updated_at: item.updated_at, data })
export const commitTestImport = (token: string, item: TestImport, t: FacultyTest) =>
  request<{ version: number }>(token, `/imports/${encodeURIComponent(item.import_id)}/commit`, 'POST', { expected_updated_at: item.updated_at, expected_version: t.version })
export const getTestHistory = (token: string, id: string) => request<TestHistory>(token, `/${encodeURIComponent(id)}/history`)

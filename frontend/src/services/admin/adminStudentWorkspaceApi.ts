import { AdminApiError } from './adminApi.ts'
import { notifySessionExpired } from '../shared/sessionEvents.ts'
import type { StudentWorkspaceApi } from '../students/studentWorkspaceApi.ts'
import type { AttendanceSection } from '../faculty/facultyAttendanceApi.ts'

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/admin/student-workspace`
async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } })
  if (response.status === 401) notifySessionExpired(token)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new AdminApiError(response.status, body.error?.message ?? 'Student workspace request failed.', body, body.error?.code ?? null)
  }
  return response.json() as Promise<T>
}
const section = (id: string) => `/sections/${encodeURIComponent(id)}`

export const adminStudentWorkspaceApi: StudentWorkspaceApi = {
  namespace: 'admin',
  getSections: async (token) => (await request<AttendanceSection[]>(token, '/sections')).map((item) => ({
    assignment_id: item.section_id, assigned_at: '', section_id: item.section_id,
    academic_year_id: item.academic_year_id ?? '', semester_id: item.semester_id ?? '',
    section: item, can_manage: item.can_manage ?? false,
  })),
  getStudents: (token, id, query) => request(token, `${section(id)}/students?${query}`),
  getProfile: (token, id, offset = 0) => request(token, `/roster/${encodeURIComponent(id)}/profile?offset=${offset}`),
  getHistory: (token, id, query) => request(token, `${section(id)}/history?${query}`),
  getRegistrations: (token, id, offset = 0, limit = 100, status, filters) => request(token, `${section(id)}/registrations?${new URLSearchParams({
    limit: String(limit), offset: String(offset), ...(status ? { registration: status } : {}),
    ...(filters?.batchId ? { batch_id: filters.batchId } : {}), ...(filters?.search ? { search: filters.search } : {}),
    ...(filters?.sort ? { sort: filters.sort } : {}),
  })}`),
  createRegistration: (token, id, data) => request(token, `${section(id)}/registrations`, { method: 'POST', body: JSON.stringify(data) }),
  getBatches: (token, id, includeInactive = false) => request(token, `${section(id)}/batches${includeInactive ? '?include_inactive=true' : ''}`),
  sendInvitation: (token, id, registrationId) => request(token, `${section(id)}/registrations/${encodeURIComponent(registrationId)}/invitation`, { method: 'POST' }),
}

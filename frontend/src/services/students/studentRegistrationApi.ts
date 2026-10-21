import { AdminApiError } from '../admin/adminApi.ts'
import { notifySessionExpired } from '../shared/sessionEvents.ts'
import type { FacultyAttendanceRosterRow } from '../faculty/facultyAttendanceApi.ts'

export interface ClassStudentRegistration {
  registration_id: string
  student_name: string
  register_number: string
  university_roll_number: string | null
  email: string | null
  program_id: string
  batch_id: string
  section_code: string
  batch_start_year: number
  batch_end_year: number
  roster_status: FacultyAttendanceRosterRow['roster_status']
  linked_student_id: string | null
  identity_conflict: boolean
  subjects_assigned: false
  invitation_delivery?: StudentInvitationDelivery
}

export interface StudentInvitationDelivery {
  registration_id: string
  status: 'sent' | 'already_sent' | 'failed' | 'pending' | 'captured'
  message: string
}

export interface ClassStudentRegistrationInput {
  student_name: string
  register_number: string
  university_roll_number?: string
  email: string
  auto_send_invitation?: boolean
  batch_id: string
}

export interface AcademicBatch {
  batch_id: string
  program_id: string
  start_year: number
  end_year: number
  is_active: boolean
}

export interface ClassRegistrationFilters {
  batchId?: string
  search?: string
  sort?: 'register_number' | 'student_name'
}

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/faculty/student-registrations/sections`

async function request<T>(token: string, scopeSectionId: string, init: RequestInit = {}, query = ''): Promise<T> {
  const response = await fetch(`${BASE}/${encodeURIComponent(scopeSectionId)}${query}`, {
    ...init, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  })
  if (response.status === 401) notifySessionExpired(token)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new AdminApiError(response.status, body.error?.message ?? 'Student registration request failed.', body, body.error?.code ?? null)
  }
  return response.json() as Promise<T>
}

export const createClassStudentRegistration = (token: string, scopeSectionId: string, data: ClassStudentRegistrationInput) =>
  request<ClassStudentRegistration>(token, scopeSectionId, { method: 'POST', body: JSON.stringify(data) })

export const sendStudentRegistrationInvitation = (token: string, scopeSectionId: string, registrationId: string) =>
  request<StudentInvitationDelivery>(token, scopeSectionId, { method: 'POST' }, `/${encodeURIComponent(registrationId)}/invitation`)

export const getClassStudentRegistrations = (token: string, scopeSectionId: string, offset = 0, limit = 100, registration?: ClassStudentRegistration['roster_status'], filters?: ClassRegistrationFilters) =>
  request<{ items: ClassStudentRegistration[]; total: number }>(token, scopeSectionId, {}, `?${new URLSearchParams({
    limit: String(limit), offset: String(offset), ...(registration ? { registration } : {}),
    ...(filters?.batchId ? { batch_id: filters.batchId } : {}), ...(filters?.search ? { search: filters.search } : {}),
    ...(filters?.sort ? { sort: filters.sort } : {}),
  })}`)

export const getRegistrationBatches = (token: string, scopeSectionId: string, includeInactive = false) =>
  request<AcademicBatch[]>(token, scopeSectionId, {}, `/batches${includeInactive ? '?include_inactive=true' : ''}`)

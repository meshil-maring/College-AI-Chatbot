import type {
  AssignmentValidity,
  FacultyContext,
  ResponsibilityManagement,
  ResponsibilityPayload,
  ResponsibilityReport,
} from '../../types/faculty.ts'
import { ADMIN_BASE, FACULTY_BASE, requestJson } from './http.ts'
export interface FacultyAssignmentPayload {
  faculty_user_id: string
  section_id: string
  start_at?: string
  end_at?: string | null
  is_active?: boolean
}

export function getFacultyAssignments(accessToken: string): Promise<{
  sections: Array<{ section_id: string; name: string; code: string; course: { name: string; code: string } }>
  faculty: Array<{ id: string; email: string; first_name: string; last_name: string }>
  assignments: Array<{
    assignment_id: string
    faculty_user_id: string
    section_id: string
    start_at?: string
    end_at?: string | null
    is_active?: boolean
    faculty: { email: string; first_name: string; last_name: string }
    section: { name: string; code: string; course: { name: string; code: string } }
  }>
}> {
  return requestJson('GET', `${ADMIN_BASE}/faculty-assignments`, accessToken)
}

export function createFacultyAssignment(
  accessToken: string,
  payload: FacultyAssignmentPayload,
): Promise<{ assignment_id: string }> {
  return requestJson('POST', `${ADMIN_BASE}/faculty-assignments`, accessToken, payload)
}

export function revokeFacultyAssignment(accessToken: string, assignmentId: string): Promise<{ assignment_id: string }> {
  return requestJson('DELETE', `${ADMIN_BASE}/faculty-assignments/${encodeURIComponent(assignmentId)}`, accessToken)
}

export function getMyFacultyAssignments(accessToken: string): Promise<
  Array<{
    assignment_id: string
    assigned_at: string
    section: { section_id: string; name: string; code: string; course: { name: string; code: string } }
  }>
> {
  return requestJson('GET', `${FACULTY_BASE}/assignments`, accessToken)
}

export interface ScopedTeachingAssignmentManagement {
  sections: Array<{
    section_id: string
    name: string
    code: string
    course: { name: string; code: string }
    program?: { name: string }
    semester?: { name: string }
    academic_year?: { name: string }
  }>
  faculty: Array<{ id: string; email: string; first_name: string; last_name: string }>
  assignments: Array<{
    assignment_id: string
    faculty_user_id: string
    section_id: string
    start_at: string
    end_at: string | null
    is_active: boolean
    revoked_at: string | null
    state: string
    faculty: { email: string; first_name: string; last_name: string } | null
    section: ScopedTeachingAssignmentManagement['sections'][number]
  }>
}

export function getScopedTeachingAssignments(accessToken: string): Promise<ScopedTeachingAssignmentManagement> {
  return requestJson('GET', `${FACULTY_BASE}/teaching-assignments/management`, accessToken)
}

export function createScopedTeachingAssignment(
  accessToken: string,
  payload: FacultyAssignmentPayload & { start_at: string; is_active: boolean },
): Promise<{ assignment_id: string }> {
  return requestJson('POST', `${FACULTY_BASE}/teaching-assignments/management`, accessToken, payload)
}

export function updateScopedTeachingAssignment(
  accessToken: string,
  assignmentId: string,
  payload: AssignmentValidity,
): Promise<{ assignment_id: string }> {
  return requestJson(
    'PATCH',
    `${FACULTY_BASE}/teaching-assignments/management/${encodeURIComponent(assignmentId)}`,
    accessToken,
    payload,
  )
}

export function revokeScopedTeachingAssignment(
  accessToken: string,
  assignmentId: string,
): Promise<{ assignment_id: string }> {
  return requestJson(
    'POST',
    `${FACULTY_BASE}/teaching-assignments/management/${encodeURIComponent(assignmentId)}/revoke`,
    accessToken,
  )
}

export const getFacultyContext = (token: string) => requestJson<FacultyContext>('GET', `${FACULTY_BASE}/context`, token)

export const getFacultyResponsibilityManagement = (token: string) =>
  requestJson<ResponsibilityManagement>('GET', `${ADMIN_BASE}/faculty-responsibilities`, token)

export const createFacultyResponsibility = (
  token: string,
  payload: ResponsibilityPayload & { faculty_user_id: string; responsibility_code: string },
) => requestJson<{ responsibility_id: string }>('POST', `${ADMIN_BASE}/faculty-responsibilities`, token, payload)

export const updateFacultyResponsibility = (token: string, id: string, payload: ResponsibilityPayload) =>
  requestJson<{ responsibility_id: string }>(
    'PATCH',
    `${ADMIN_BASE}/faculty-responsibilities/${encodeURIComponent(id)}`,
    token,
    payload,
  )

export const revokeFacultyResponsibility = (token: string, id: string) =>
  requestJson<{ responsibility_id: string }>(
    'DELETE',
    `${ADMIN_BASE}/faculty-responsibilities/${encodeURIComponent(id)}`,
    token,
  )

export const updateFacultyTeachingValidity = (token: string, id: string, payload: AssignmentValidity) =>
  requestJson<{ assignment_id: string }>(
    'PATCH',
    `${ADMIN_BASE}/faculty-assignments/${encodeURIComponent(id)}`,
    token,
    payload,
  )

export const getFacultyResponsibilityReport = (token: string, id: string) =>
  requestJson<ResponsibilityReport>('GET', `${FACULTY_BASE}/responsibilities/${encodeURIComponent(id)}/report`, token)

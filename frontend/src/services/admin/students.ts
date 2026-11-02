import type { PendingStudent } from '../../types/admin/students.ts'
import type {
  StudentDirectoryFilter,
  StudentDirectoryResponse,
  StudentInvitationUpdateResult,
  StudentInvitationUpdateInput,
  StudentProfileUpdateInput,
  StudentInvitation,
  StudentInvitationBulkResult,
  StudentInvitationCreated,
  StudentInvitationInput,
  StudentInvitationList,
  StudentIdentityReviewRequest,
  StudentIdentityReviewResponse,
} from '../../types/admin/students.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

/** Tenant and decision permissions are resolved by the server; no actor or tenant is submitted. */
export function listPendingStudents(accessToken: string, limit = 100, offset = 0): Promise<PendingStudent[]> {
  return requestJson('GET', `${ADMIN_BASE}/students/pending?limit=${limit}&offset=${offset}`, accessToken)
}
export function approvePendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson('POST', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/approve`, accessToken)
}
export function rejectPendingStudent(accessToken: string, studentId: string): Promise<PendingStudent> {
  return requestJson('POST', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/reject`, accessToken)
}

const ONBOARDING = `${ADMIN_BASE}/students/onboarding-invitations`

export function getStudentDirectory(
  accessToken: string,
  filters: {
    search?: string
    status?: Exclude<StudentDirectoryFilter, 'all'>
    programId?: string
    limit: number
    offset: number
  },
): Promise<StudentDirectoryResponse> {
  const query = new URLSearchParams({
    limit: String(filters.limit),
    offset: String(filters.offset),
  })
  if (filters.search) query.set('search', filters.search)
  if (filters.status) query.set('status', filters.status)
  if (filters.programId) query.set('program_id', filters.programId)
  return requestJson('GET', `${ADMIN_BASE}/students/directory?${query}`, accessToken)
}

export function updateStudentProfile(
  accessToken: string,
  studentId: string,
  input: StudentProfileUpdateInput,
): Promise<{ student_id: string; updated: boolean }> {
  return requestJson('PATCH', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}`, accessToken, input)
}

export function setStudentActive(
  accessToken: string,
  studentId: string,
  active: boolean,
): Promise<{ student_id: string; is_active: boolean }> {
  const action = active ? 'reactivate' : 'deactivate'
  return requestJson('POST', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}/${action}`, accessToken)
}

export function deleteStudentProfile(
  accessToken: string,
  studentId: string,
): Promise<{ student_id: string; deleted: boolean }> {
  return requestJson('DELETE', `${ADMIN_BASE}/students/${encodeURIComponent(studentId)}`, accessToken)
}

export function listStudentInvitations(accessToken: string): Promise<StudentInvitationList> {
  return requestJson('GET', ONBOARDING, accessToken)
}

export function createStudentInvitation(
  accessToken: string,
  academicSectionId: string,
  student: StudentInvitationInput,
): Promise<StudentInvitationCreated> {
  return requestJson('POST', ONBOARDING, accessToken, {
    ...student,
    academic_section_id: academicSectionId,
  })
}

export function reviewStudentIdentity(
  accessToken: string,
  identity: StudentIdentityReviewRequest,
): Promise<StudentIdentityReviewResponse> {
  return requestJson('POST', `${ONBOARDING}/review`, accessToken, identity)
}

export function createStudentInvitationsBulk(
  accessToken: string,
  academicSectionId: string,
  students: StudentInvitationInput[],
): Promise<StudentInvitationBulkResult> {
  return requestJson('POST', `${ONBOARDING}/bulk`, accessToken, {
    academic_section_id: academicSectionId,
    students,
  })
}

export function resendStudentInvitation(accessToken: string, invitationId: string): Promise<StudentInvitationCreated> {
  return requestJson('POST', `${ONBOARDING}/${encodeURIComponent(invitationId)}/resend`, accessToken)
}

export function reassignStudentInvitation(
  accessToken: string,
  invitationId: string,
  academicSectionId: string,
): Promise<StudentInvitation> {
  return requestJson('PATCH', `${ONBOARDING}/${encodeURIComponent(invitationId)}/section`, accessToken, {
    academic_section_id: academicSectionId,
  })
}

export function updateStudentInvitation(
  accessToken: string,
  invitationId: string,
  input: StudentInvitationUpdateInput,
): Promise<StudentInvitationUpdateResult> {
  return requestJson('PATCH', `${ONBOARDING}/${encodeURIComponent(invitationId)}`, accessToken, input)
}

export function cancelStudentInvitation(
  accessToken: string,
  invitationId: string,
): Promise<{ invitation_id: string; cancelled: boolean }> {
  return requestJson('DELETE', `${ONBOARDING}/${encodeURIComponent(invitationId)}`, accessToken)
}

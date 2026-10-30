import type {
  ChoiceGroupDraft,
  RegistrationCatalogue,
  SemesterAssignment,
  StudentSemesterList,
} from '../../types/semesterRegistration.ts'
import { ADMIN_BASE, STUDENT_BASE, requestJson } from '../admin/http.ts'

const BASE = `${ADMIN_BASE}/academic-registration`

export function getRegistrationCatalogue(token: string, signal?: AbortSignal): Promise<RegistrationCatalogue> {
  return requestJson('GET', BASE, token, undefined, signal)
}
export function saveChoiceGroup(token: string, draft: ChoiceGroupDraft, id?: string) {
  return requestJson<{ choice_group_id: string; institution_id: string }>(
    id ? 'PATCH' : 'POST',
    `${BASE}/option-groups${id ? `/${encodeURIComponent(id)}` : ''}`,
    token,
    draft,
  )
}
export function deleteChoiceGroup(token: string, id: string) {
  return requestJson<{ choice_group_id: string; institution_id: string }>(
    'DELETE',
    `${BASE}/option-groups/${encodeURIComponent(id)}`,
    token,
  )
}
export function assignStudentSemester(
  token: string,
  studentId: string,
  sectionId: string,
): Promise<SemesterAssignment> {
  return requestJson('POST', `${BASE}/assignments`, token, {
    student_id: studentId,
    academic_section_id: sectionId,
  })
}
export function getMySemesters(token: string, signal?: AbortSignal): Promise<StudentSemesterList> {
  return requestJson('GET', `${STUDENT_BASE}/me/semester-registrations`, token, undefined, signal)
}
export function completeMySemester(token: string, id: string, options: string[]): Promise<SemesterAssignment> {
  return requestJson('POST', `${STUDENT_BASE}/me/semester-registrations/${encodeURIComponent(id)}/complete`, token, {
    selected_option_ids: options,
  })
}

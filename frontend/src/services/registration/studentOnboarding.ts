import { API_BASE_URL, requestJson } from './client.ts'

export interface StudentInvitationDetails {
  status: 'pending' | 'accepted'
  student_name: string
  email: string
  institution_name: string
  batch_name: string
  batch_code: string
  section_name: string
  section_active: boolean
  expires_at: string
}

export interface StudentInvitationCompletion {
  message: string
  completed: boolean
}

const BASE = `${API_BASE_URL}/v1/student-onboarding`

export function inspectStudentSetup(token: string): Promise<StudentInvitationDetails> {
  return requestJson('POST', `${BASE}/inspect`, { token }, 15_000)
}

export function completeStudentSetup(token: string, password: string): Promise<StudentInvitationCompletion> {
  return requestJson('POST', `${BASE}/complete`, { token, password }, 30_000)
}

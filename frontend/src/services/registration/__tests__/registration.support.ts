import { beforeEach, vi } from 'vitest'
export const INSTITUTION = {
  institution_id: 'b0000000-0000-0000-0000-0000000000a1',
  code: 'IMPHAL',
  name: 'Imphal College',
}

export const REGISTRATION_RESPONSE = {
  message: 'Student registration submitted.',
  user_id: '71000000-0000-0000-0000-000000000001',
  institution_id: INSTITUTION.institution_id,
  institution_code: 'IMPHAL',
  registration_type: 'student',
  approval_status: 'pending',
  student_id: '30000000-0000-0000-0000-000000000151',
  request_id: null,
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

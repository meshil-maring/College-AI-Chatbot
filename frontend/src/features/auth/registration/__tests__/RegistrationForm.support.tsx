import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, vi } from 'vitest'
import * as registration from '../../../../services/registration/registration.ts'
import type { InstitutionLookupResponse, RegistrationResponse } from '../../../../types/registration.ts'
vi.mock('../../../../services/registration/registration.ts', async () => {
  const actual = await vi.importActual<typeof import('../../../../services/registration/registration.ts')>(
    '../../../../services/registration/registration.ts',
  )
  return {
    ...actual,
    lookupInstitution: vi.fn(),
    registerStudent: vi.fn(),
    registerFaculty: vi.fn(),
    registerStaff: vi.fn(),
  }
})

export const INSTITUTION: InstitutionLookupResponse = {
  institution_id: 'b0000000-0000-0000-0000-0000000000a1',
  code: 'IMPHAL',
  name: 'Imphal College',
}

export const REGISTRATION_RESPONSE: RegistrationResponse = {
  message: 'Student registration submitted. Your account is pending approval by the institution admin.',
  user_id: '71000000-0000-0000-0000-000000000001',
  institution_id: INSTITUTION.institution_id,
  institution_code: 'IMPHAL',
  registration_type: 'student',
  approval_status: 'pending',
  student_id: '30000000-0000-0000-0000-000000000151',
  request_id: null,
}

export function regError(
  kind: registration.RegistrationErrorKind,
  status: number | null,
  code: string | null,
): registration.RegistrationError {
  return new registration.RegistrationError(kind, status, code)
}

export async function fillValidForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
  await user.type(screen.getByLabelText('Email'), 'jane@example.com')
  await user.type(screen.getByLabelText('Register Number'), '1001')
  await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
  await user.type(screen.getByLabelText('Password'), 'secret123')
  await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
  // Blur the institution code so the form resolves it before submission,
  // then wait for the lookup to settle (success OR controlled failure).
  await user.tab()
  await waitFor(() => expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument())
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(registration.lookupInstitution).mockResolvedValue(INSTITUTION)
  vi.mocked(registration.registerStudent).mockResolvedValue(REGISTRATION_RESPONSE)
  vi.mocked(registration.registerFaculty).mockResolvedValue({
    ...REGISTRATION_RESPONSE,
    message: 'Faculty registration submitted. Your account is pending approval by the institution admin.',
    registration_type: 'faculty',
    student_id: null,
    request_id: '72000000-0000-0000-0000-000000000001',
  })
  vi.mocked(registration.registerStaff).mockResolvedValue({
    ...REGISTRATION_RESPONSE,
    message: 'Staff registration submitted. Your account is pending approval by the institution admin.',
    registration_type: 'staff',
    student_id: null,
    request_id: '72000000-0000-0000-0000-000000000002',
  })
})

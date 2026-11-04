import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const mocks = vi.hoisted(() => ({
  complete: vi.fn(),
  inspect: vi.fn(),
  login: vi.fn(),
}))

vi.mock('../../../services/registration/studentOnboarding.ts', () => ({
  completeStudentSetup: mocks.complete,
  inspectStudentSetup: mocks.inspect,
}))
vi.mock('../session/AuthProvider.tsx', () => ({
  useAuth: () => ({ login: mocks.login }),
}))

import StudentSetupPage from './StudentSetupPage.tsx'

const invitation = {
  status: 'pending' as const,
  student_name: 'Student Example',
  email: 'student@example.edu',
  institution_name: 'Example College',
  batch_name: '2026 Batch',
  batch_code: 'B26',
  section_name: 'Section A',
  section_active: true,
  expires_at: '2099-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.resetAllMocks()
  window.history.replaceState(null, '', '/student-setup#setup-token')
  mocks.inspect.mockResolvedValue(invitation)
  mocks.complete.mockResolvedValue({ message: 'Setup complete.', completed: true })
  mocks.login.mockResolvedValue(false)
})

describe('student account setup', () => {
  it('offers student login when automatic sign-in fails after password setup', async () => {
    const user = userEvent.setup()
    render(<StudentSetupPage />)

    await screen.findByText('Account email:')
    await user.type(screen.getByLabelText('Create password'), 'student-password')
    await user.type(screen.getByLabelText('Confirm password'), 'student-password')
    await user.click(screen.getByRole('button', { name: 'Verify and set password' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Your account is ready, but automatic sign-in failed. Please sign in to continue.',
    )
    expect(mocks.complete).toHaveBeenCalledWith('setup-token', 'student-password')
    expect(mocks.login).toHaveBeenCalledWith('student@example.edu', 'student-password')
    expect(screen.getByRole('link', { name: 'Continue to student login' })).toHaveAttribute('href', '/login/student')
  })
})

/**
 * DEVELOPMENT / TESTING ONLY — tests for ChangePasswordForm.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChangePasswordForm from './ChangePasswordForm.tsx'
import * as devAuth from '../../services/devAuth.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, devChangePassword: vi.fn() }
})

vi.mock('./AuthProvider.tsx', () => ({
  useAuth: () => ({
    status: 'authenticated',
    user: { authenticated: true, user_id: 'u1', auth_user_id: 'a1', email: 'student@college.edu' },
    accessToken: 'test-token',
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

describe('ChangePasswordForm', () => {
  it('shows a validation error when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText(/current password/i), 'oldpass123')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'different123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/do not match/i)
    expect(devAuth.devChangePassword).not.toHaveBeenCalled()
  })

  it('submits and shows a success message', async () => {
    vi.mocked(devAuth.devChangePassword).mockResolvedValueOnce({ message: 'ok' })
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText(/current password/i), 'oldpass123')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'newpass123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/successfully/i)
    })
    expect(devAuth.devChangePassword).toHaveBeenCalledWith({
      email: 'student@college.edu',
      current_password: 'oldpass123',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })
  })

  it('shows a failure message when the current password is wrong', async () => {
    vi.mocked(devAuth.devChangePassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('invalid_credentials', 400),
    )
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText(/current password/i), 'wrongpass')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'newpass123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect/i)
  })
})

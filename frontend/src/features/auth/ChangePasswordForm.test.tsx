/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChangePasswordForm from './ChangePasswordForm.tsx'
import * as auth from '../../services/auth.ts'

const authState = vi.hoisted(() => ({ accessToken: 'access-token' as string | null }))

vi.mock('./AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

vi.mock('../../services/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/auth.ts')>(
    '../../services/auth.ts',
  )
  return { ...actual, changePassword: vi.fn() }
})

beforeEach(() => {
  vi.clearAllMocks()
  authState.accessToken = 'access-token'
  vi.mocked(auth.changePassword).mockResolvedValue({ message: 'changed' })
})

describe('ChangePasswordForm', () => {
  it('requires the current password and an eight-character new password', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('New password'), 'short')
    await user.type(screen.getByLabelText('Confirm new password'), 'short')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByText('Please enter your current password.')).toBeInTheDocument()
    expect(screen.getByText('Password must be at least 8 characters.')).toBeInTheDocument()
    expect(auth.changePassword).not.toHaveBeenCalled()
  })

  it('submits through the authenticated API and clears plaintext fields', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('Current password'), 'oldpass123')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/successfully/i)
    expect(auth.changePassword).toHaveBeenCalledWith(
      'access-token',
      'oldpass123',
      'newpass123',
      'newpass123',
    )
    expect((screen.getByLabelText('Current password') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('New password') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Confirm new password') as HTMLInputElement).value).toBe('')
  })

  it('uses a safe response when the current credential cannot be verified', async () => {
    vi.mocked(auth.changePassword).mockRejectedValueOnce(
      new auth.AuthError('password_verification', 400, 'PASSWORD_VERIFICATION_FAILED'),
    )
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('Current password'), 'wrongpass')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Current credentials could not be verified.',
    )
  })
})

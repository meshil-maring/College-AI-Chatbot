/**
 * DEVELOPMENT / TESTING ONLY — tests for ForgotPasswordForm.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForgotPasswordForm from './ForgotPasswordForm.tsx'
import * as devAuth from '../../services/devAuth.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, devForgotPassword: vi.fn() }
})

describe('ForgotPasswordForm', () => {
  it('shows a validation error for an invalid email', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'newpass123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/valid email/i)
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  }, 15000)

  it('shows a validation error when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText(/email/i), 'student@college.edu')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'different123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/do not match/i)
  })

  it('submits and shows a success message', async () => {
    vi.mocked(devAuth.devForgotPassword).mockResolvedValueOnce({ message: 'ok' })
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText(/email/i), 'student@college.edu')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'newpass123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/successfully/i)
    })
    expect(devAuth.devForgotPassword).toHaveBeenCalledWith({
      email: 'student@college.edu',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })
  })

  it('shows a failure message when the reset fails', async () => {
    vi.mocked(devAuth.devForgotPassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('user_not_found', 404),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText(/email/i), 'nobody@college.edu')
    await user.type(screen.getByLabelText(/^new password$/i), 'newpass123')
    await user.type(screen.getByLabelText(/confirm new password/i), 'newpass123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no account/i)
  })

  it('calls onBackToLogin when "Back to sign in" is clicked', async () => {
    const onBackToLogin = vi.fn()
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={onBackToLogin} />)

    await user.click(screen.getByRole('button', { name: /back to sign in/i }))
    expect(onBackToLogin).toHaveBeenCalled()
  })
})

/// <reference types="vitest/globals" />
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ResetPasswordForm from './ResetPasswordForm.tsx'
import * as auth from '../../services/auth.ts'

vi.mock('../../services/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/auth.ts')>(
    '../../services/auth.ts',
  )
  return { ...actual, completePasswordReset: vi.fn() }
})

beforeEach(() => {
  window.history.replaceState(null, '', '/reset-password')
  window.localStorage.clear()
  vi.mocked(auth.completePasswordReset).mockReset()
  vi.mocked(auth.completePasswordReset).mockResolvedValue({ message: 'ok' })
})

afterEach(() => {
  window.history.replaceState(null, '', '/')
})

describe('ResetPasswordForm', () => {
  it('rejects an absent or invalid recovery token', async () => {
    window.history.replaceState(null, '', '/reset-password#type=signup&access_token=not-recovery')
    render(<ResetPasswordForm onBackToLogin={vi.fn()} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid or has expired/i)
    expect(window.location.hash).toBe('')
    expect(screen.queryByLabelText('New password')).not.toBeInTheDocument()
    expect(auth.completePasswordReset).not.toHaveBeenCalled()
  })

  it('consumes a recovery token without persisting it in browser storage or history', async () => {
    window.history.replaceState(
      null,
      '',
      '/reset-password#access_token=recovery-access-token&type=recovery&refresh_token=provider-refresh',
    )
    const user = userEvent.setup()
    render(<ResetPasswordForm onBackToLogin={vi.fn()} />)

    expect(await screen.findByLabelText('New password')).toBeInTheDocument()
    expect(window.location.hash).toBe('')
    await user.type(screen.getByLabelText('New password'), 'new-recovery-password')
    await user.type(screen.getByLabelText('Confirm new password'), 'new-recovery-password')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/please sign in/i)
    expect(auth.completePasswordReset).toHaveBeenCalledWith(
      'recovery-access-token',
      'new-recovery-password',
      'new-recovery-password',
    )
    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)
  })

  it('does not submit a short password', async () => {
    window.history.replaceState(
      null,
      '',
      '/reset-password#access_token=recovery-access-token&type=recovery',
    )
    const user = userEvent.setup()
    render(<ResetPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('New password'), 'short')
    await user.type(screen.getByLabelText('Confirm new password'), 'short')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Password must be at least 8 characters.',
    )
    expect(auth.completePasswordReset).not.toHaveBeenCalled()
  })
})

/**
 * DEVELOPMENT / TESTING ONLY — tests for ChangePasswordForm (Phase 6.15.6).
 *
 * Covers rendering, per-field validation, loading / duplicate-submission
 * prevention, the generic backend error, password visibility, clearing of the
 * plaintext fields after a successful update, and session behaviour (the
 * backend revokes nothing, so the form must NOT sign the user out).
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChangePasswordForm from './ChangePasswordForm.tsx'
import * as devAuth from '../../services/devAuth.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, devChangePassword: vi.fn() }
})

interface MockUser {
  authenticated: boolean
  user_id: string
  auth_user_id: string
  email: string | null
}

/** Mutable auth context so tests can drive the account email and logout. */
const authState = vi.hoisted(() => ({
  user: null as MockUser | null,
  logout: vi.fn(),
}))

vi.mock('./AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

type User = ReturnType<typeof userEvent.setup>

async function fillValidForm(user: User): Promise<void> {
  await user.type(screen.getByLabelText('Current password'), 'oldpass123')
  await user.type(screen.getByLabelText('New password'), 'newpass123')
  await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
}

beforeEach(() => {
  vi.clearAllMocks()
  authState.user = {
    authenticated: true,
    user_id: 'u1',
    auth_user_id: 'a1',
    email: 'student@college.edu',
  }
  vi.mocked(devAuth.devChangePassword).mockResolvedValue({ message: 'ok' })
})

describe('ChangePasswordForm — rendering', () => {
  it('renders the three password fields and the dev-only notice', () => {
    render(<ChangePasswordForm />)

    expect(screen.getByLabelText('Current password')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Confirm new password')).toHaveAttribute('type', 'password')
    expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument()
    expect(screen.getByText(/development \/ testing only/i)).toBeInTheDocument()
  })
})

describe('ChangePasswordForm — validation', () => {
  it('requires the current password before contacting the backend', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please enter your current password.',
    )
    expect(devAuth.devChangePassword).not.toHaveBeenCalled()
  })

  it('requires a new password of at least 6 characters', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('Current password'), 'oldpass123')
    await user.type(screen.getByLabelText('New password'), 'abc')
    await user.type(screen.getByLabelText('Confirm new password'), 'abc')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Password must be at least 6 characters.',
    )
    expect(devAuth.devChangePassword).not.toHaveBeenCalled()
  })

  it('shows a validation error when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('Current password'), 'oldpass123')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'different123')
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
    expect(devAuth.devChangePassword).not.toHaveBeenCalled()
  })
})

describe('ChangePasswordForm — submission and session behaviour', () => {
  it('submits the backend schema, clears the plaintext fields and keeps the session active', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/successfully/i)
    expect(devAuth.devChangePassword).toHaveBeenCalledWith({
      email: 'student@college.edu',
      current_password: 'oldpass123',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })

    // Plaintext passwords never linger in the form after the update.
    expect((screen.getByLabelText('Current password') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('New password') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Confirm new password') as HTMLInputElement).value).toBe('')

    // The backend does not revoke sessions on a password change, so the form
    // must NOT sign the user out.
    expect(authState.logout).not.toHaveBeenCalled()
  })

  it('shows the generic message when the current password is rejected', async () => {
    vi.mocked(devAuth.devChangePassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('invalid_credentials', 400),
    )
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('The current password is incorrect.')
    expect(authState.logout).not.toHaveBeenCalled()
  })

  it('fails safely when the account email cannot be determined', async () => {
    authState.user = {
      authenticated: true,
      user_id: 'u1',
      auth_user_id: 'a1',
      email: null,
    }
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Your account email could not be determined. Please sign in again.',
    )
    expect(devAuth.devChangePassword).not.toHaveBeenCalled()
  })

  it('shows "Updating…" and prevents duplicate submissions while in flight', async () => {
    let resolveUpdate!: (value: devAuth.DevAuthMessageResponse) => void
    vi.mocked(devAuth.devChangePassword).mockImplementation(
      () =>
        new Promise<devAuth.DevAuthMessageResponse>((resolve) => {
          resolveUpdate = resolve
        }),
    )
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /change password/i }))

    const busyButton = screen.getByRole('button', { name: /updating/i })
    expect(busyButton).toBeDisabled()
    expect(screen.getByLabelText('Current password')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Show new password' })).toBeDisabled()

    await user.click(busyButton)
    expect(devAuth.devChangePassword).toHaveBeenCalledTimes(1)

    resolveUpdate({ message: 'ok' })
    expect(await screen.findByRole('status')).toHaveTextContent(/successfully/i)
  })
})

describe('ChangePasswordForm — password visibility', () => {
  it('toggles the visibility of the field it belongs to only', async () => {
    const user = userEvent.setup()
    render(<ChangePasswordForm />)

    await user.type(screen.getByLabelText('Current password'), 'oldpass123')
    await user.click(screen.getByRole('button', { name: 'Show current password' }))

    expect(screen.getByLabelText('Current password')).toHaveAttribute('type', 'text')
    expect((screen.getByLabelText('Current password') as HTMLInputElement).value).toBe('oldpass123')
    // The other fields stay hidden.
    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Confirm new password')).toHaveAttribute('type', 'password')
  })
})


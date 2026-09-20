/**
 * DEVELOPMENT / TESTING ONLY — tests for ForgotPasswordForm (Phase 6.15.6).
 *
 * Covers rendering, field-level validation, generic anti-enumeration success,
 * generic error handling (never an account-existence signal), loading /
 * duplicate-submission prevention, password visibility and clearing, and the
 * existing back-to-login navigation.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForgotPasswordForm, { RECOVERY_SUBMITTED_MESSAGE } from './ForgotPasswordForm.tsx'
import * as devAuth from '../../services/devAuth.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, devForgotPassword: vi.fn() }
})

type User = ReturnType<typeof userEvent.setup>

async function fillValidForm(user: User): Promise<void> {
  await user.type(screen.getByLabelText('Email'), 'student@college.edu')
  await user.type(screen.getByLabelText('New password'), 'newpass123')
  await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
}

function submitReset(user: User): Promise<void> {
  return user.click(screen.getByRole('button', { name: /^reset password$/i }))
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
  window.sessionStorage.clear()
  vi.mocked(devAuth.devForgotPassword).mockResolvedValue({ message: 'ok' })
})

describe('ForgotPasswordForm — rendering', () => {
  it('renders the email field, both password fields, the dev-only notice and navigation', () => {
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email')
    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Confirm new password')).toHaveAttribute('type', 'password')
    expect(screen.getByRole('button', { name: /^reset password$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back to login/i })).toBeInTheDocument()
    expect(screen.getByText(/development \/ testing only/i)).toBeInTheDocument()
  })

  it('offers email only — no register number, roll number, or institution code recovery', () => {
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    expect(screen.queryByLabelText(/register number/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/roll number/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/institution code/i)).not.toBeInTheDocument()
  })
})

describe('ForgotPasswordForm — field validation', () => {
  it('reports every empty required field without calling the backend', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await submitReset(user)

    const alerts = await screen.findAllByRole('alert')
    expect(alerts.map((alert) => alert.textContent)).toEqual([
      'Please enter your email address.',
      'Please enter a new password.',
      'Please confirm your new password.',
    ])
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  })

  it('rejects an invalid email address', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter a valid email address.')
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  })

  it('rejects a password shorter than the backend minimum (6 characters)', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'student@college.edu')
    await user.type(screen.getByLabelText('New password'), 'abc')
    await user.type(screen.getByLabelText('Confirm new password'), 'abc')
    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Password must be at least 6 characters.',
    )
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  })

  it('rejects mismatched passwords', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'student@college.edu')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'different123')
    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  })

  it('associates the invalid field with its error message', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('New password'), 'newpass123')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpass123')
    await submitReset(user)

    const email = screen.getByLabelText('Email')
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(email).toHaveAttribute('aria-describedby', 'recovery-email-error')
    expect(screen.getByText('Please enter a valid email address.')).toHaveAttribute(
      'id',
      'recovery-email-error',
    )
  })

  it('clears a field error as soon as the user edits the form', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await submitReset(user)
    expect(await screen.findByText('Please enter your email address.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Email'), 's')

    expect(screen.queryByText('Please enter your email address.')).not.toBeInTheDocument()
  })
})

describe('ForgotPasswordForm — submission and anti-enumeration', () => {
  it('submits the backend schema and shows the generic, enumeration-safe outcome', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)

    expect(await screen.findByText('Password Reset Submitted')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(RECOVERY_SUBMITTED_MESSAGE)
    expect(devAuth.devForgotPassword).toHaveBeenCalledWith({
      email: 'student@college.edu',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })
    // The outcome wording is identical for a known and an unknown account.
    expect(RECOVERY_SUBMITTED_MESSAGE).toContain('If an account exists for this email')
    expect(screen.queryByText(/no account/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/does not exist/i)).not.toBeInTheDocument()
  })

  it('never authenticates the user and never persists a credential', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)
    await screen.findByText('Password Reset Submitted')

    // No token of any kind is written by the recovery flow.
    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)
    // The plaintext passwords are gone from the UI with the form.
    expect(screen.queryByLabelText('New password')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Confirm new password')).not.toBeInTheDocument()
  })

  it('never renders account-existence wording for an unexpected not-found error', async () => {
    vi.mocked(devAuth.devForgotPassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('user_not_found', 404),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      'We could not complete the password reset. Please try again.',
    )
    expect(alert).not.toHaveTextContent(/no account/i)
    expect(alert).not.toHaveTextContent(/not found/i)
  })

  it('shows a generic message when the backend reports a server error', async () => {
    vi.mocked(devAuth.devForgotPassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('server', 500),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The server reported an error. Please try again later.',
    )
  })

  it('shows the dev-only disabled message when the feature gate is off', async () => {
    vi.mocked(devAuth.devForgotPassword).mockRejectedValueOnce(
      new devAuth.DevAuthError('disabled', 404),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This development-only feature is disabled.',
    )
  })

  it('shows "Resetting password…" and prevents duplicate submissions while in flight', async () => {
    let resolveReset!: (value: devAuth.DevAuthMessageResponse) => void
    vi.mocked(devAuth.devForgotPassword).mockImplementation(
      () =>
        new Promise<devAuth.DevAuthMessageResponse>((resolve) => {
          resolveReset = resolve
        }),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await submitReset(user)

    const busyButton = screen.getByRole('button', { name: /resetting password/i })
    expect(busyButton).toBeDisabled()
    expect(screen.getByLabelText('Email')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Show new password' })).toBeDisabled()

    await user.click(busyButton)
    expect(devAuth.devForgotPassword).toHaveBeenCalledTimes(1)

    resolveReset({ message: 'ok' })
    expect(await screen.findByText('Password Reset Submitted')).toBeInTheDocument()
  })
})

describe('ForgotPasswordForm — navigation and password visibility', () => {
  it('returns to the login screen from the form', async () => {
    const onBackToLogin = vi.fn()
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={onBackToLogin} />)

    await user.click(screen.getByRole('button', { name: /back to login/i }))

    expect(onBackToLogin).toHaveBeenCalledTimes(1)
  })

  it('returns to the login screen from the success state', async () => {
    const onBackToLogin = vi.fn()
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={onBackToLogin} />)

    await fillValidForm(user)
    await submitReset(user)
    await screen.findByText('Password Reset Submitted')

    await user.click(screen.getByRole('button', { name: /back to login/i }))

    expect(onBackToLogin).toHaveBeenCalledTimes(1)
  })

  it('toggles the new-password visibility without submitting anything', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('New password'), 'newpass123')
    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show new password' }))

    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'text')
    expect((screen.getByLabelText('New password') as HTMLInputElement).value).toBe('newpass123')
    expect(devAuth.devForgotPassword).not.toHaveBeenCalled()
  })
})


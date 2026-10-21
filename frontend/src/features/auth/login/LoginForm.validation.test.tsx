import './__tests__/LoginForm.support.tsx'
import { authState } from './__tests__/LoginForm.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as devAuth from '../../../services/auth/devAuth.ts'
import { SESSION_EXPIRED_MESSAGE } from '../../../services/shared/sessionEvents.ts'
import LoginForm from './LoginForm.tsx'
describe('LoginForm — student approval guidance', () => {
  it.each(['general', 'student'] as const)(
    'explains approval on the %s login without inferring account status',
    (audience) => {
      render(<LoginForm audience={audience} />)
      expect(screen.getByText(/New student accounts need institutional approval/)).toBeInTheDocument()
      expect(screen.getByLabelText('Email, Register Number or University Roll Number')).toHaveAttribute(
        'aria-describedby',
        'student-approval-help',
      )
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    },
  )

  it.each(['faculty', 'staff', 'admin', 'super_admin'] as const)(
    'keeps student-specific guidance off the %s login',
    (audience) => {
      render(<LoginForm audience={audience} />)
      expect(screen.queryByText(/New student accounts need institutional approval/)).not.toBeInTheDocument()
    },
  )
})

describe('LoginForm — password field (Phase 6.15.6)', () => {
  it('toggles the password visibility without submitting', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    const input = await screen.findByLabelText('Password')
    await user.type(input, 'secret123')
    expect(input).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show password' }))

    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
    expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('secret123')
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('disables the visibility toggle while signing in', async () => {
    authState.status = 'authenticating'
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    expect(await screen.findByRole('button', { name: 'Show password' })).toBeDisabled()
  })
})

describe('LoginForm — client-side validation (Phase 6.15.6)', () => {
  it('requires an identifier before submitting', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(await screen.findByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please enter your email, register number, or university roll number.',
    )
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('requires the institution code when an academic identifier is used', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(await screen.findByLabelText('Email, Register Number or University Roll Number'), 'REG2026001')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please enter your institution code to sign in with a register number or roll number.',
    )
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('requires a password of at least 6 characters', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'meshil@example.com',
    )
    await user.type(screen.getByLabelText('Password'), 'abc')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Password must be at least 6 characters.')
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('clears the validation message as soon as the user edits a field', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(await screen.findByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter your email')

    await user.type(screen.getByLabelText('Email, Register Number or University Roll Number'), 'm')

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('LoginForm — session expiry (Phase 6.15.6)', () => {
  it('shows the shared session-expired message when a saved session is rejected', async () => {
    authState.error = SESSION_EXPIRED_MESSAGE
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Your session has expired. Please log in again.')
    // The login screen renders the exact message the session-expiry bus
    // publishes, so expiry is never reported as invalid credentials.
    expect(SESSION_EXPIRED_MESSAGE).toBe('Your session has expired. Please log in again.')
    expect(alert).not.toHaveTextContent(/invalid login credentials/i)
  })
})

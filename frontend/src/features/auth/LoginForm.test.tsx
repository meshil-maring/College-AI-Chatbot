/**
 * LoginForm tests.
 *
 * Phase 5.4: "Forgot Password?" dev/test gating.
 * Phase 6.15.2: registration navigation.
 * Phase 6.15.3: unified identifier field (email / register number /
 * university roll number), conditional institution-code field, loading
 * state, duplicate-submission prevention, and error display.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from './LoginForm.tsx'
import * as devAuth from '../../services/devAuth.ts'
import { SESSION_EXPIRED_MESSAGE } from '../../services/sessionEvents.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, fetchDevAuthStatus: vi.fn() }
})

/** Mutable auth context mock so each test can drive status/error/login. */
const authState = vi.hoisted(() => ({
  status: 'unauthenticated' as string,
  user: null,
  accessToken: null,
  error: null as string | null,
  login: vi.fn<(identifier: string, password: string, institutionCode?: string) => Promise<void>>(),
  logout: vi.fn(),
}))

vi.mock('./AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

beforeEach(() => {
  authState.status = 'unauthenticated'
  authState.error = null
  authState.login.mockReset()
  authState.login.mockResolvedValue(undefined)
  vi.mocked(devAuth.fetchDevAuthStatus).mockReset()
})

describe('LoginForm — dev/test "Forgot Password?" gating', () => {
  it('hides the Forgot Password link when dev/test mode is disabled', async () => {
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await waitFor(() => {
      expect(devAuth.fetchDevAuthStatus).toHaveBeenCalled()
    })
    expect(screen.queryByText(/forgot password/i)).not.toBeInTheDocument()
  })

  it('shows the Forgot Password link when dev/test mode is enabled', async () => {
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: true })
    render(<LoginForm />)

    expect(await screen.findByText(/forgot password/i)).toBeInTheDocument()
  })
})

describe('LoginForm — registration navigation', () => {
  it('shows the registration form when "Register as Student" is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.click(
      await screen.findByRole('button', { name: /register as student/i }),
    )
    // The registration form is uniquely identifiable by its institution-code
    // resolution UX, which the login form does not have.
    expect(await screen.findByLabelText('Institution Code')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /^sign in$/i }),
    ).not.toBeInTheDocument()
  })

  it('returns to the login form via "Back to Login" on the registration form', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.click(
      await screen.findByRole('button', { name: /register as student/i }),
    )
    await screen.findByLabelText('Institution Code')
    await user.click(screen.getByRole('button', { name: /back to login/i }))

    expect(await screen.findByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
    expect(screen.queryByLabelText('Institution Code')).not.toBeInTheDocument()
  })
})

describe('LoginForm — unified identifier field (Phase 6.15.3)', () => {
  it('renders the identifier and password fields', async () => {
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    expect(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('hides the Institution Code field for an email identifier', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'meshil@example.com',
    )

    expect(screen.queryByLabelText('Institution Code')).not.toBeInTheDocument()
  })

  it('shows and requires the Institution Code field for a register number', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'REG2026001',
    )

    const codeInput = await screen.findByLabelText('Institution Code')
    expect(codeInput).toBeInTheDocument()
    expect(codeInput).toHaveAttribute('required')
  })
})

describe('LoginForm — submission payload (Phase 6.15.3)', () => {
  it('submits an email login WITHOUT an institution code', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'meshil@example.com',
    )
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    await waitFor(() => {
      expect(authState.login).toHaveBeenCalledTimes(1)
    })
    expect(authState.login).toHaveBeenCalledWith('meshil@example.com', 'secret123', undefined)
  })

  it('submits a register-number login WITH the institution code', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'REG2026001',
    )
    await user.type(screen.getByLabelText('Institution Code'), 'GIT')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    await waitFor(() => {
      expect(authState.login).toHaveBeenCalledTimes(1)
    })
    expect(authState.login).toHaveBeenCalledWith('REG2026001', 'secret123', 'GIT')
  })

  it('submits a roll-number login WITH the institution code', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'UNI20260001',
    )
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    await waitFor(() => {
      expect(authState.login).toHaveBeenCalledTimes(1)
    })
    expect(authState.login).toHaveBeenCalledWith('UNI20260001', 'secret123', 'IMPHAL')
  })

  it('does NOT submit an academic identifier without the institution code', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'REG2026001',
    )
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    expect(authState.login).not.toHaveBeenCalled()
  })
})

describe('LoginForm — loading state and duplicate submission (Phase 6.15.3)', () => {
  it('disables the form and shows the busy label while authenticating', async () => {
    authState.status = 'authenticating'
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    const button = await screen.findByRole('button', { name: /signing in/i })
    expect(button).toBeDisabled()
    expect(screen.getByLabelText('Email, Register Number or University Roll Number')).toBeDisabled()
    expect(screen.getByLabelText('Password')).toBeDisabled()
  })

  it('prevents duplicate submission while a login is running', async () => {
    const user = userEvent.setup()
    authState.status = 'authenticating'
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'meshil@example.com',
    )
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /signing in/i }))
    await user.click(screen.getByRole('button', { name: /signing in/i }))

    expect(authState.login).not.toHaveBeenCalled()
  })
})

describe('LoginForm — authentication error display (Phase 6.15.3)', () => {
  it('renders the user-safe auth error in the alert region', async () => {
    authState.error = 'Invalid login credentials. Please check your details and try again.'
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      'Invalid login credentials. Please check your details and try again.',
    )
  })
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

    await user.type(
      await screen.findByLabelText('Email, Register Number or University Roll Number'),
      'REG2026001',
    )
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

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Password must be at least 6 characters.',
    )
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('clears the validation message as soon as the user edits a field', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.type(await screen.findByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter your email')

    await user.type(
      screen.getByLabelText('Email, Register Number or University Roll Number'),
      'm',
    )

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


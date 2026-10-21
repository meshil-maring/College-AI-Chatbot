import './__tests__/LoginForm.support.tsx'
import { authState } from './__tests__/LoginForm.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AuthError } from '../../../services/auth/auth.ts'
import * as devAuth from '../../../services/auth/devAuth.ts'
import * as registration from '../../../services/registration/registration.ts'
import LoginForm from './LoginForm.tsx'
describe('LoginForm — password recovery', () => {
  it('always offers the production recovery flow', async () => {
    render(<LoginForm />)

    await userEvent.setup().click(screen.getByRole('button', { name: /forgot password/i }))
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send recovery instructions/i })).toBeInTheDocument()
  })
})

describe('LoginForm — registration navigation', () => {
  it('opens student registration directly from a university link and preserves its code', async () => {
    window.history.replaceState({}, '', '/login/student?institution=QUEST123&register=1')
    try {
      render(<LoginForm audience="student" />)
      expect(screen.getByLabelText('Institution Code')).toHaveValue('QUEST123')
      expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: /back to login/i }))
      expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
      expect(authState.login).not.toHaveBeenCalled()
    } finally {
      window.history.replaceState({}, '', '/')
    }
  })

  it('returns from successful student registration to login without signing in', async () => {
    const user = userEvent.setup()
    vi.mocked(registration.lookupInstitution).mockResolvedValue({
      institution_id: 'fixture-institution',
      code: 'TEST',
      name: 'Synthetic College',
    })
    vi.mocked(registration.registerStudent).mockResolvedValue({
      message: 'Registration submitted.',
      user_id: 'fixture-user',
      institution_id: 'fixture-institution',
      institution_code: 'TEST',
      registration_type: 'student',
      approval_status: 'pending',
      student_id: 'fixture-student',
      request_id: null,
    })
    render(<LoginForm audience="student" />)
    await user.click(screen.getByRole('button', { name: /register as student/i }))
    await user.type(screen.getByLabelText('Full Name'), 'Synthetic Student')
    await user.type(screen.getByLabelText('Email'), 'synthetic@example.com')
    await user.type(screen.getByLabelText('Register Number'), 'TEST1001')
    await user.type(screen.getByLabelText('Institution Code'), 'TEST')
    await user.type(screen.getByLabelText('Password'), 'test-password')
    await user.type(screen.getByLabelText('Confirm Password'), 'test-password')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('status')).toHaveTextContent('Awaiting institutional approval')
    expect(screen.getByText('Synthetic College')).toBeInTheDocument()
    expect(authState.login).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Back to Login' }))
    expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
    expect(screen.getByText(/New student accounts need institutional approval/)).toBeInTheDocument()
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('shows the registration form when "Register as Student" is clicked', async () => {
    const user = userEvent.setup()
    render(<LoginForm />)

    await user.click(await screen.findByRole('button', { name: /register as student/i }))
    // The registration form is uniquely identifiable by its institution-code
    // resolution UX, which the login form does not have.
    expect(await screen.findByLabelText('Institution Code')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^sign in$/i })).not.toBeInTheDocument()
  })

  it('returns to the login form via "Back to Login" on the registration form', async () => {
    const user = userEvent.setup()
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await user.click(await screen.findByRole('button', { name: /register as student/i }))
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

    expect(await screen.findByLabelText('Email, Register Number or University Roll Number')).toBeInTheDocument()
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

    await user.type(await screen.findByLabelText('Email, Register Number or University Roll Number'), 'REG2026001')

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

    await user.type(await screen.findByLabelText('Email, Register Number or University Roll Number'), 'REG2026001')
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

    await user.type(await screen.findByLabelText('Email, Register Number or University Roll Number'), 'UNI20260001')
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

    await user.type(await screen.findByLabelText('Email, Register Number or University Roll Number'), 'REG2026001')
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
    authState.error = new AuthError('invalid_credentials', 401, 'INVALID_CREDENTIALS').message
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Invalid login credentials. Please check your details and try again.')
    expect(alert).toHaveTextContent('For help with account approval or access, contact your administrator.')
    expect(alert).not.toHaveTextContent(/pending|rejected|inactive/)
  })
})

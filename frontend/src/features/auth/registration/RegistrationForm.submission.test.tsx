import './__tests__/RegistrationForm.support.tsx'
import { fillValidForm, regError } from './__tests__/RegistrationForm.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as registration from '../../../services/registration/registration.ts'
import RegistrationForm from './RegistrationForm.tsx'
describe('RegistrationForm — institution lookup', () => {
  it('shows a controlled message when the lookup fails on the network', async () => {
    vi.mocked(registration.lookupInstitution).mockRejectedValue(regError('network', null, null))
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.tab()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reach the backend. Please make sure the server is running, then try again.',
    )
  })

  it('refuses to submit when the institution could not be resolved', async () => {
    vi.mocked(registration.lookupInstitution).mockRejectedValue(
      regError('institution_not_found', 404, 'INSTITUTION_NOT_FOUND'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(registration.registerStudent).not.toHaveBeenCalled()
  })
})

describe('RegistrationForm — registration submission', () => {
  it('submits the exact backend registration schema and shows pending approval', async () => {
    const user = userEvent.setup()
    const onBackToLogin = vi.fn()
    render(<RegistrationForm onBackToLogin={onBackToLogin} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(registration.registerStudent).toHaveBeenCalledTimes(1)
    expect(registration.registerStudent).toHaveBeenCalledWith({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
      register_number: '1001',
      university_roll_number: null,
    })

    // Pending-approval success state — NOT an authenticated session.
    expect(await screen.findByText('Registration Successful')).toBeInTheDocument()
    expect(screen.getByText('Your student account has been created.')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Awaiting institutional approval')
    expect(screen.getByRole('status')).toHaveAttribute('aria-atomic', 'true')
    expect(screen.getByRole('heading', { name: 'Registration Successful' })).toHaveFocus()
    expect(screen.getByText('Imphal College')).toBeInTheDocument()
    expect(screen.getByText(/administrator or authorized staff member will review/)).toHaveTextContent(
      'You can sign in after your account has been approved.',
    )
    expect(screen.getByText(/Email verification is separate/)).toBeInTheDocument()
    expect(screen.getByText(/After approval, return to login/)).toHaveTextContent('IMPHAL')
    expect(screen.getByText(/For questions about your registration/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Email')).not.toBeInTheDocument()
  })

  it('submits the university roll number when the register number is absent', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('University Roll Number'), '2026-1001')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
    await user.tab()
    await waitFor(() => expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(registration.registerStudent).toHaveBeenCalledWith(
      expect.objectContaining({
        register_number: null,
        university_roll_number: '2026-1001',
      }),
    )
    expect(await screen.findByText('Registration Successful')).toBeInTheDocument()
  })

  it('splits a multi-token full name into first and last name', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Anna Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Register Number'), '1001')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
    await user.tab()
    await waitFor(() => expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(registration.registerStudent).toHaveBeenCalledWith(
      expect.objectContaining({ first_name: 'Jane', last_name: 'Anna Doe' }),
    )
  })

  // ======================================================================
  // Phase 6.15.5 — password retention & tokenless-registration invariants
  // ======================================================================
  it('drops the password after submission: no password retention in UI or storage', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    // The success screen replaces the form: every password input is gone
    // from the UI the moment the submission completes.
    expect(await screen.findByText('Registration Successful')).toBeInTheDocument()
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Confirm Password')).not.toBeInTheDocument()

    // §20 audit — no credential of any kind reaches browser storage during
    // registration (no token, no password).
    expect(window.localStorage.getItem('college-ai-chatbot.access-token')).toBeNull()
    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)

    // A freshly mounted registration form never pre-fills credentials —
    // the submitted password is not retained across form instances.
    unmount()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)
    expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Confirm Password') as HTMLInputElement).value).toBe('')
  })

  it('never authenticates after registration: no token exists in browser storage', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    // Pending-approval success state — NOT a session.
    expect(await screen.findByText('Registration Successful')).toBeInTheDocument()

    // The registration contract issues no token: nothing may be persisted
    // under the AuthProvider storage key, and browser storage stays empty
    // (no token, no credentials) after registration.
    expect(window.localStorage.getItem('college-ai-chatbot.access-token')).toBeNull()
    expect(window.sessionStorage.length).toBe(0)
    expect(window.localStorage.length).toBe(0)
  })
})

describe('RegistrationForm — duplicate and failure handling', () => {
  it('shows a controlled message for a duplicate email', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError('email_already_registered', 409, 'EMAIL_ALREADY_REGISTERED'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('An account with this email already exists.')
    expect(screen.queryByText('Registration Successful')).not.toBeInTheDocument()
  })

  it('shows a controlled message for a duplicate register number', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError('register_number_already_registered', 409, 'REGISTER_NUMBER_ALREADY_REGISTERED'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This register number is already registered.')
  })

  it('shows a controlled message for a duplicate university roll number', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError('roll_number_already_registered', 409, 'ROLL_NUMBER_ALREADY_REGISTERED'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This university roll number is already registered.')
  })

  it('shows a controlled message for a backend validation error', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(regError('validation', 422, 'VALIDATION_ERROR'))
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Please review the highlighted fields and try again.')
  })

  it('shows a controlled message when registration fails on the network', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(regError('network', null, null))
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reach the backend. Please make sure the server is running, then try again.',
    )
  })
})

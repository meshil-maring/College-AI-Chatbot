/**
 * Phase 6.15.2 — Registration form tests.
 *
 * Covers rendering, client-side validation, institution-code resolution UX,
 * registration submission (request shape, duplicate errors, network
 * failures), the pending-approval success state, and navigation.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegistrationForm from './RegistrationForm.tsx'
import * as registration from '../../services/registration.ts'
import type {
  InstitutionLookupResponse,
  RegistrationResponse,
} from '../../types/registration.ts'

vi.mock('../../services/registration.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/registration.ts')>(
    '../../services/registration.ts',
  )
  return { ...actual, lookupInstitution: vi.fn(), registerStudent: vi.fn() }
})

const INSTITUTION: InstitutionLookupResponse = {
  institution_id: 'b0000000-0000-0000-0000-0000000000a1',
  code: 'IMPHAL',
  name: 'Imphal College',
}

const REGISTRATION_RESPONSE: RegistrationResponse = {
  message:
    'Student registration submitted. Your account is pending approval by the institution admin.',
  user_id: '71000000-0000-0000-0000-000000000001',
  institution_id: INSTITUTION.institution_id,
  institution_code: 'IMPHAL',
  registration_type: 'student',
  approval_status: 'pending',
  student_id: '30000000-0000-0000-0000-000000000151',
  request_id: null,
}

function regError(
  kind: registration.RegistrationErrorKind,
  status: number | null,
  code: string | null,
): registration.RegistrationError {
  return new registration.RegistrationError(kind, status, code)
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
  await user.type(screen.getByLabelText('Email'), 'jane@example.com')
  await user.type(screen.getByLabelText('Register Number'), '1001')
  await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
  await user.type(screen.getByLabelText('Password'), 'secret123')
  await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
  // Blur the institution code so the form resolves it before submission,
  // then wait for the lookup to settle (success OR controlled failure).
  await user.tab()
  await waitFor(() =>
    expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument(),
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(registration.lookupInstitution).mockResolvedValue(INSTITUTION)
  vi.mocked(registration.registerStudent).mockResolvedValue(REGISTRATION_RESPONSE)
})

describe('RegistrationForm — rendering', () => {
  it('renders all required fields and navigation controls', () => {
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Register Number')).toBeInTheDocument()
    expect(screen.getByLabelText('University Roll Number')).toBeInTheDocument()
    expect(screen.getByLabelText('Institution Code')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /create account/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /back to login/i }),
    ).toBeInTheDocument()
  })

  it('navigates back to login from the form', async () => {
    const user = userEvent.setup()
    const onBackToLogin = vi.fn()
    render(<RegistrationForm onBackToLogin={onBackToLogin} />)

    await user.click(screen.getByRole('button', { name: /back to login/i }))
    expect(onBackToLogin).toHaveBeenCalledTimes(1)
  })
})

describe('RegistrationForm — client-side validation', () => {
  it('rejects empty required fields', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please enter your full name.',
    )
    expect(registration.registerStudent).not.toHaveBeenCalled()
  })

  it('rejects an invalid email', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please enter a valid email address.',
    )
  })

  it('requires at least one academic identifier (backend IDENTIFIER_REQUIRED)', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter at least one of register number or university roll number.',
    )
  })

  it('rejects a password shorter than the backend minimum (6 characters)', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Register Number'), '1001')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'abc')
    await user.type(screen.getByLabelText('Confirm Password'), 'abc')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Password must be at least 6 characters.',
    )
  })

  it('rejects mismatched password confirmation', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Register Number'), '1001')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'different')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Passwords do not match.',
    )
  })
})

describe('RegistrationForm — institution lookup', () => {
  it('shows the institution name after a successful lookup', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.tab()
    expect(registration.lookupInstitution).toHaveBeenCalledWith('IMPHAL')
    expect(await screen.findByText('Imphal College')).toBeInTheDocument()
  })

  it('shows a controlled error for an unknown institution code', async () => {
    vi.mocked(registration.lookupInstitution).mockRejectedValue(
      regError('institution_not_found', 404, 'INSTITUTION_NOT_FOUND'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Institution Code'), 'NOPE99')
    await user.tab()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Institution code was not found. Please check the code and try again.',
    )
  })

  it('shows a loading state while the lookup is in flight', async () => {
    let resolveLookup!: (value: InstitutionLookupResponse) => void
    vi.mocked(registration.lookupInstitution).mockImplementation(
      () =>
        new Promise<InstitutionLookupResponse>((resolve) => {
          resolveLookup = resolve
        }),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.tab()
    expect(screen.getByText('Finding institution…')).toBeInTheDocument()

    resolveLookup(INSTITUTION)
    expect(await screen.findByText('Imphal College')).toBeInTheDocument()
  })

  it('shows a controlled message when the lookup fails on the network', async () => {
    vi.mocked(registration.lookupInstitution).mockRejectedValue(
      regError('network', null, null),
    )
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
    expect(
      await screen.findByText('Registration Successful'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Your student account has been created.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'Your account is currently waiting for approval from your college administrator or staff.',
      ),
    ).toBeInTheDocument()
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
    await waitFor(() =>
      expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument(),
    )
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
    await waitFor(() =>
      expect(screen.queryByText('Finding institution…')).not.toBeInTheDocument(),
    )
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
    expect(
      await screen.findByText('Registration Successful'),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Confirm Password')).not.toBeInTheDocument()

    // §20 audit — no credential of any kind reaches browser storage during
    // registration (no token, no password).
    expect(
      window.localStorage.getItem('college-ai-chatbot.access-token'),
    ).toBeNull()
    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)

    // A freshly mounted registration form never pre-fills credentials —
    // the submitted password is not retained across form instances.
    unmount()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)
    expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('')
    expect(
      (screen.getByLabelText('Confirm Password') as HTMLInputElement).value,
    ).toBe('')
  })

  it('never authenticates after registration: no token exists in browser storage', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    // Pending-approval success state — NOT a session.
    expect(
      await screen.findByText('Registration Successful'),
    ).toBeInTheDocument()

    // The registration contract issues no token: nothing may be persisted
    // under the AuthProvider storage key, and browser storage stays empty
    // (no token, no credentials) after registration.
    expect(
      window.localStorage.getItem('college-ai-chatbot.access-token'),
    ).toBeNull()
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

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'An account with this email already exists.',
    )
    expect(screen.queryByText('Registration Successful')).not.toBeInTheDocument()
  })

  it('shows a controlled message for a duplicate register number', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError(
        'register_number_already_registered',
        409,
        'REGISTER_NUMBER_ALREADY_REGISTERED',
      ),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This register number is already registered.',
    )
  })

  it('shows a controlled message for a duplicate university roll number', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError(
        'roll_number_already_registered',
        409,
        'ROLL_NUMBER_ALREADY_REGISTERED',
      ),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This university roll number is already registered.',
    )
  })

  it('shows a controlled message for a backend validation error', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError('validation', 422, 'VALIDATION_ERROR'),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please review the highlighted fields and try again.',
    )
  })

  it('shows a controlled message when registration fails on the network', async () => {
    vi.mocked(registration.registerStudent).mockRejectedValue(
      regError('network', null, null),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reach the backend. Please make sure the server is running, then try again.',
    )
  })
})

describe('RegistrationForm — loading states and approval flow', () => {
  it('disables the submit button and prevents duplicate submissions while creating the account', async () => {
    let resolveSubmit!: (value: RegistrationResponse) => void
    vi.mocked(registration.registerStudent).mockImplementation(
      () =>
        new Promise<RegistrationResponse>((resolve) => {
          resolveSubmit = resolve
        }),
    )
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    const submittingButton = screen.getByRole('button', {
      name: /creating account/i,
    })
    expect(submittingButton).toBeDisabled()
    expect(screen.getByLabelText('Email')).toBeDisabled()

    resolveSubmit(REGISTRATION_RESPONSE)
    expect(await screen.findByText('Registration Successful')).toBeInTheDocument()
    expect(registration.registerStudent).toHaveBeenCalledTimes(1)
  })

  it('navigates back to login from the pending-approval success state', async () => {
    const user = userEvent.setup()
    const onBackToLogin = vi.fn()
    render(<RegistrationForm onBackToLogin={onBackToLogin} />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await screen.findByText('Registration Successful')

    const successBackButton = screen.getAllByRole('button', {
      name: /back to login/i,
    })
    expect(successBackButton).toHaveLength(1)
    await user.click(successBackButton[0])
    expect(onBackToLogin).toHaveBeenCalledTimes(1)
  })
})

describe('RegistrationForm — password visibility (Phase 6.15.6)', () => {
  it('toggles each password field independently, preserving the values', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'secret123')

    // Only the targeted field is revealed.
    await user.click(screen.getByRole('button', { name: 'Show confirm password' }))
    expect(screen.getByLabelText('Confirm Password')).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show password' }))
    const password = screen.getByLabelText('Password')
    expect(password).toHaveAttribute('type', 'text')
    expect((password as HTMLInputElement).value).toBe('secret123')

    // The toggle never submits the form.
    expect(registration.registerStudent).not.toHaveBeenCalled()
  })
})

import './__tests__/RegistrationForm.support.tsx'
import { INSTITUTION, regError } from './__tests__/RegistrationForm.support.tsx'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as registration from '../../../services/registration/registration.ts'
import type { InstitutionLookupResponse } from '../../../types/registration.ts'
import RegistrationForm from './RegistrationForm.tsx'
describe('institution lookup races', () => {
  it('ignores an old lookup after the institution code changes', async () => {
    let finish!: (value: InstitutionLookupResponse) => void
    vi.mocked(registration.lookupInstitution).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    render(<RegistrationForm onBackToLogin={vi.fn()} />)
    const input = screen.getByLabelText('Institution Code')
    fireEvent.change(input, { target: { value: 'IMPHAL' } })
    fireEvent.blur(input)
    fireEvent.change(input, { target: { value: 'OTHER' } })
    await act(async () => {
      finish(INSTITUTION)
    })
    expect(screen.queryByText('Imphal College')).not.toBeInTheDocument()
    expect(registration.registerStudent).not.toHaveBeenCalled()
  })

  it('keeps the institution selected at the gateway', () => {
    window.history.replaceState(null, '', '/login/student?institution=IMPHAL')
    try {
      render(<RegistrationForm onBackToLogin={vi.fn()} />)
      expect(screen.getByLabelText('Institution Code')).toHaveValue('IMPHAL')
    } finally {
      window.history.replaceState(null, '', '/')
    }
  })
})

describe('RegistrationForm — faculty registration', () => {
  it('shows faculty fields and submits a pending faculty membership request', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm registrationType="faculty" onBackToLogin={vi.fn()} />)

    expect(screen.queryByLabelText('Register Number')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('University Roll Number')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Full Name'), 'Ada Lovelace')
    await user.type(screen.getByLabelText('Email'), 'ada@example.com')
    await user.type(screen.getByLabelText(/Designation/), 'Professor')
    await user.type(screen.getByLabelText(/Department/), 'Computer Science')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(registration.registerFaculty).toHaveBeenCalledTimes(1))
    expect(registration.registerFaculty).toHaveBeenCalledWith({
      registration_type: 'faculty',
      institution_code: 'IMPHAL',
      email: 'ada@example.com',
      password: 'secret123',
      first_name: 'Ada',
      last_name: 'Lovelace',
      designation: 'Professor',
      department: 'Computer Science',
    })
    expect(await screen.findByText('Your faculty registration has been submitted.')).toBeInTheDocument()
  })
})

describe('RegistrationForm — staff registration', () => {
  it('shows staff fields and submits a pending staff membership request', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm registrationType="staff" onBackToLogin={vi.fn()} />)

    expect(screen.queryByLabelText('Register Number')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('University Roll Number')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Full Name'), 'Grace Hopper')
    await user.type(screen.getByLabelText('Email'), 'grace@example.com')
    await user.type(screen.getByLabelText(/Designation/), 'Registrar')
    await user.type(screen.getByLabelText(/Department/), 'Admissions')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.type(screen.getByLabelText('Confirm Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(registration.registerStaff).toHaveBeenCalledTimes(1))
    expect(registration.registerStaff).toHaveBeenCalledWith({
      registration_type: 'staff',
      institution_code: 'IMPHAL',
      email: 'grace@example.com',
      password: 'secret123',
      first_name: 'Grace',
      last_name: 'Hopper',
      designation: 'Registrar',
      department: 'Admissions',
    })
    expect(await screen.findByText('Your staff registration has been submitted.')).toBeInTheDocument()
  })
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
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back to login/i })).toBeInTheDocument()
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
    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter your full name.')
    expect(registration.registerStudent).not.toHaveBeenCalled()
  })

  it('rejects an invalid email', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter a valid email address.')
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

  it('rejects a password shorter than the backend minimum (8 characters)', async () => {
    const user = userEvent.setup()
    render(<RegistrationForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Full Name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Register Number'), '1001')
    await user.type(screen.getByLabelText('Institution Code'), 'IMPHAL')
    await user.type(screen.getByLabelText('Password'), 'abc')
    await user.type(screen.getByLabelText('Confirm Password'), 'abc')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Password must be at least 8 characters.')
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
    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
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
})

import './__tests__/RegistrationForm.support.tsx'
import { REGISTRATION_RESPONSE, fillValidForm } from './__tests__/RegistrationForm.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as registration from '../../../services/registration/registration.ts'
import type { RegistrationResponse } from '../../../types/registration.ts'
import RegistrationForm from './RegistrationForm.tsx'
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
    await user.tab()
    expect(successBackButton[0]).toHaveFocus()
    await user.keyboard('{Enter}')
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

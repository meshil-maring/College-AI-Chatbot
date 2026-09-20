/**
 * Phase 6.15.6 — tests for the shared PasswordField (visibility toggle,
 * label/error association, keyboard operation, disabled state).
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PasswordField from './PasswordField.tsx'

describe('PasswordField', () => {
  it('associates its visible label with the input', () => {
    render(<PasswordField label="Password" name="password" value="" onChange={vi.fn()} />)

    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('type', 'password')
    expect(input).toHaveAttribute('id', 'password-input')
  })

  it('toggles only its own input between hidden and visible, preserving the value', async () => {
    const user = userEvent.setup()
    render(
      <PasswordField
        label="New password"
        name="newPassword"
        value="secret123"
        onChange={vi.fn()}
      />,
    )

    const input = screen.getByLabelText('New password')
    const showButton = screen.getByRole('button', { name: 'Show new password' })
    // The control is tied to exactly one input.
    expect(showButton).toHaveAttribute('aria-controls', 'newPassword-input')
    expect(showButton).toHaveTextContent('Show')

    await user.click(showButton)

    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'text')
    expect((screen.getByLabelText('New password') as HTMLInputElement).value).toBe('secret123')

    await user.click(screen.getByRole('button', { name: 'Hide new password' }))
    expect(screen.getByLabelText('New password')).toHaveAttribute('type', 'password')
  })

  it('is keyboard operable', async () => {
    const user = userEvent.setup()
    render(<PasswordField label="Password" name="password" value="" onChange={vi.fn()} />)

    const toggle = screen.getByRole('button', { name: 'Show password' })
    toggle.focus()
    expect(toggle).toHaveFocus()
    await user.keyboard('{Enter}')

    expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
  })

  it('renders the field error next to the input and links it via aria-describedby', () => {
    render(
      <PasswordField
        label="New password"
        name="newPassword"
        value=""
        onChange={vi.fn()}
        error="Password must be at least 6 characters."
      />,
    )

    const input = screen.getByLabelText('New password')
    const error = screen.getByRole('alert')

    expect(error).toHaveTextContent('Password must be at least 6 characters.')
    expect(error).toHaveAttribute('id', 'newPassword-error')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'newPassword-error')
  })

  it('leaves a valid field without aria-invalid / aria-describedby', () => {
    render(<PasswordField label="Password" name="password" value="" onChange={vi.fn()} />)

    const input = screen.getByLabelText('Password')
    expect(input).not.toHaveAttribute('aria-invalid')
    expect(input).not.toHaveAttribute('aria-describedby')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables the input AND the toggle while an operation is running', () => {
    render(<PasswordField label="Password" name="password" value="" onChange={vi.fn()} disabled />)

    expect(screen.getByLabelText('Password')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Show password' })).toBeDisabled()
  })

  it('never renders the plaintext value outside the input itself', () => {
    render(<PasswordField label="Password" name="password" value="topsecret" onChange={vi.fn()} />)

    expect(screen.queryByText('topsecret')).not.toBeInTheDocument()
  })
})

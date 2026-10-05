/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForgotPasswordForm, { RECOVERY_SUBMITTED_MESSAGE } from './ForgotPasswordForm.tsx'
import * as auth from '../../services/auth.ts'

vi.mock('../../services/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/auth.ts')>(
    '../../services/auth.ts',
  )
  return { ...actual, requestPasswordRecovery: vi.fn() }
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(auth.requestPasswordRecovery).mockResolvedValue({ message: 'ok' })
})

describe('ForgotPasswordForm', () => {
  it('submits only the email and shows the same generic recovery response', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('Email'), 'student@college.edu')
    await user.click(screen.getByRole('button', { name: /send recovery instructions/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(RECOVERY_SUBMITTED_MESSAGE)
    expect(auth.requestPasswordRecovery).toHaveBeenCalledWith('student@college.edu')
    expect(screen.queryByText(/does not exist|no account/i)).not.toBeInTheDocument()
  })

  it('validates email before making the recovery request', async () => {
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'invalid')
    await user.click(screen.getByRole('button', { name: /send recovery instructions/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Please enter a valid email address.')
    expect(auth.requestPasswordRecovery).not.toHaveBeenCalled()
  })

  it('keeps provider failures controlled', async () => {
    vi.mocked(auth.requestPasswordRecovery).mockRejectedValueOnce(
      new auth.AuthError('server', 503, 'AUTH_RECOVERY_UNAVAILABLE'),
    )
    const user = userEvent.setup()
    render(<ForgotPasswordForm onBackToLogin={vi.fn()} />)

    await user.type(screen.getByLabelText('Email'), 'student@college.edu')
    await user.click(screen.getByRole('button', { name: /send recovery instructions/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The authentication server reported an error. Please try again later.',
    )
  })
})

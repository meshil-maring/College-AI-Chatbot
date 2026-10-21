import './__tests__/AdminInvitationPage.support.tsx'
import { ACCEPTED, acceptSpy, inspectSpy, PASSWORD, TOKEN } from './__tests__/AdminInvitationPage.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { AdminInvitationError } from '../../services/invitations/adminInvitationApi.ts'
import AdminInvitationPage from './AdminInvitationPage.tsx'
describe('Phase 7.14 invitation acceptance page', () => {
  it('offers no retry for an expired invitation', async () => {
    inspectSpy.mockRejectedValue(new AdminInvitationError(410, 'This invitation has expired.', 'INVITATION_EXPIRED'))
    render(<AdminInvitationPage token={TOKEN} />)

    expect(await screen.findByRole('heading', { name: /This invitation cannot be used/i })).toBeDefined()
    expect(screen.getByText('This invitation has expired.')).toBeDefined()
    // There is no password form to retry with.
    expect(screen.queryByLabelText('Password')).toBeNull()
    expect(screen.getByRole('link', { name: /Go to admin login/i })).toBeDefined()
  })

  it('offers no retry for an already-consumed invitation', async () => {
    inspectSpy.mockRejectedValue(
      new AdminInvitationError(410, 'This invitation has already been used.', 'INVITATION_ALREADY_ACCEPTED'),
    )
    render(<AdminInvitationPage token={TOKEN} />)

    expect(await screen.findByText('This invitation has already been used.')).toBeDefined()
    expect(screen.queryByLabelText('Password')).toBeNull()
  })

  it('refuses to submit a mismatched or too-short password without calling the API', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), 'short')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'different')
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    expect(await screen.findByRole('alert')).toBeDefined()
    expect(acceptSpy).not.toHaveBeenCalled()
  })

  it('sets up the account and redirects to the ordinary admin login', async () => {
    acceptSpy.mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    await waitFor(() => {
      expect(acceptSpy).toHaveBeenCalledWith(TOKEN, { password: PASSWORD })
    })
    expect(await screen.findByText(/Your University Admin account is ready/i)).toBeDefined()
    // The person signs in normally — this flow never mints a session.
    const link = screen.getByRole('link', { name: /Continue to admin login/i })
    expect(link.getAttribute('href')).toBe('/login/admin')
  })

  it('never sends a role, institution or scope alongside the password', async () => {
    acceptSpy.mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('First name (optional)'), 'Dana')
    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    await waitFor(() => {
      expect(acceptSpy).toHaveBeenCalledWith(TOKEN, {
        password: PASSWORD,
        first_name: 'Dana',
      })
    })
    const payload = acceptSpy.mock.calls[0][1] as Record<string, unknown>
    expect(Object.keys(payload).sort()).toEqual(['first_name', 'password'])
    expect(payload.role).toBeUndefined()
    expect(payload.institution_id).toBeUndefined()
    expect(payload.scope).toBeUndefined()
  })

  it('keeps the form and shows a retryable error on a transient failure', async () => {
    acceptSpy.mockRejectedValue(new AdminInvitationError(500, 'Please try again.', 'INVITATION_ACCEPTANCE_FAILED'))
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    // Retryable: the form is still usable.
    expect(await screen.findByText('Please try again.')).toBeDefined()
    expect(screen.getByLabelText('Password')).toBeDefined()
  })

  it('stops offering the form when acceptance reveals a terminal failure', async () => {
    acceptSpy.mockRejectedValue(
      new AdminInvitationError(410, 'This invitation has already been used.', 'INVITATION_ALREADY_ACCEPTED'),
    )
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    expect(await screen.findByRole('heading', { name: /This invitation cannot be used/i })).toBeDefined()
    expect(screen.queryByLabelText('Password')).toBeNull()
  })
})

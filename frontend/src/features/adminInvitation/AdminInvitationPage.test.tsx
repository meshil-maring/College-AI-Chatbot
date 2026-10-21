import './__tests__/AdminInvitationPage.support.tsx'
import {
  ACCEPTED,
  acceptSpy,
  authState,
  inspectSpy,
  INVITATION,
  membershipSpy,
  PASSWORD,
  recoverSpy,
  TOKEN,
} from './__tests__/AdminInvitationPage.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AdminInvitationError } from '../../services/invitations/adminInvitationApi.ts'
import AdminInvitationPage from './AdminInvitationPage.tsx'
describe('B05 accepted account confirmation recovery', () => {
  it('recovers after reload without signing in or entering credentials', async () => {
    inspectSpy.mockResolvedValue({ ...INVITATION, status: 'accepted', account_recovery_available: true })
    recoverSpy.mockResolvedValue(ACCEPTED)
    const page = render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('button', { name: 'Retry account recovery' })
    page.unmount()
    render(<AdminInvitationPage token={TOKEN} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Retry account recovery' }))
    await screen.findByRole('heading', { name: 'Your account is ready' })
    expect(recoverSpy).toHaveBeenCalledExactlyOnceWith(TOKEN)
    expect(acceptSpy).not.toHaveBeenCalled()
    expect(membershipSpy).not.toHaveBeenCalled()
    expect(screen.queryByLabelText(/^Password$/)).not.toBeInTheDocument()
  })

  it.each(['timeout', 'confirmation'])('switches to recovery after %s and retries safely', async (failure) => {
    acceptSpy.mockRejectedValue(
      failure === 'timeout'
        ? new Error('response lost')
        : new AdminInvitationError(502, 'Confirmation uncertain', 'INVITATION_EMAIL_CONFIRMATION_UNCERTAIN'),
    )
    inspectSpy
      .mockResolvedValueOnce(INVITATION)
      .mockResolvedValue({ ...INVITATION, status: 'accepted', account_recovery_available: true })
    recoverSpy
      .mockRejectedValueOnce(
        new AdminInvitationError(502, 'Confirmation uncertain', 'INVITATION_EMAIL_CONFIRMATION_UNCERTAIN'),
      )
      .mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByLabelText(/^Password$/)
    await userEvent.type(screen.getByLabelText(/^Password$/), PASSWORD)
    await userEvent.type(screen.getByLabelText(/Confirm password/), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: 'Create my account' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Retry account recovery' }))
    await screen.findByRole('alert')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry account recovery' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Retry account recovery' }))
    await screen.findByRole('heading', { name: 'Your account is ready' })
    expect(acceptSpy).toHaveBeenCalledTimes(1)
    expect(recoverSpy).toHaveBeenCalledTimes(2)
    expect(membershipSpy).not.toHaveBeenCalled()
  })
})

describe('B05 existing-account membership acceptance', () => {
  it('requires sign-in and provides a return-to-invitation instruction', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join/ })
    await userEvent.click(screen.getByRole('button', { name: 'I already have an account' }))
    expect(screen.getByRole('link', { name: /Sign in, then return/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept membership' })).toBeDisabled()
    expect(screen.queryByLabelText(/^Password$/)).not.toBeInTheDocument()
  })

  it('uses the authenticated membership endpoint with no password input', async () => {
    authState.status = 'authenticated'
    authState.accessToken = 'verified-session'
    authState.user = { email: INVITATION.email }
    membershipSpy.mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join/ })
    expect(screen.queryByLabelText(/^Password$/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Accept membership' }))
    await screen.findByRole('heading', { name: 'Your account is ready' })
    expect(membershipSpy).toHaveBeenCalledWith(TOKEN, 'verified-session')
    expect(acceptSpy).not.toHaveBeenCalled()
  })

  it('refuses a signed-in recipient mismatch before acceptance', async () => {
    authState.status = 'authenticated'
    authState.accessToken = 'verified-session'
    authState.user = { email: 'someone@example.test' }
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join/ })
    await userEvent.click(screen.getByRole('button', { name: 'Accept membership' }))
    expect(screen.getByRole('alert')).toHaveTextContent('belongs to another account')
    expect(membershipSpy).not.toHaveBeenCalled()
  })

  it('lets the authenticated recipient recover an already-accepted result', async () => {
    authState.status = 'authenticated'
    authState.accessToken = 'verified-session'
    authState.user = { email: INVITATION.email }
    inspectSpy.mockResolvedValue({ ...INVITATION, status: 'accepted' })
    membershipSpy.mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByText(/already been accepted/)
    await userEvent.click(screen.getByRole('button', { name: 'Accept membership' }))
    await screen.findByRole('heading', { name: 'Your account is ready' })
    expect(membershipSpy).toHaveBeenCalledWith(TOKEN, 'verified-session')
  })

  it.each([
    [410, 'INVITATION_EXPIRED', 'This invitation has expired'],
    [409, 'INVITATION_RECONCILIATION_REQUIRED', 'This acceptance requires reconciliation'],
    [403, 'FORBIDDEN', 'This invitation belongs to another account'],
    [401, 'AUTH_REQUIRED', 'Sign in with the invited account'],
  ])('handles HTTP %s %s without creating an account', async (status, code, message) => {
    authState.status = 'authenticated'
    authState.accessToken = 'verified-session'
    authState.user = { email: INVITATION.email }
    membershipSpy.mockRejectedValue(new AdminInvitationError(status, message, code))
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join/ })
    await userEvent.click(screen.getByRole('button', { name: 'Accept membership' }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(message))
    expect(acceptSpy).not.toHaveBeenCalled()
    if (code === 'INVITATION_RECONCILIATION_REQUIRED') {
      expect(screen.queryByRole('button', { name: 'Accept membership' })).not.toBeInTheDocument()
    }
  })
})

describe('Phase 7.14 invitation acceptance page', () => {
  it('validates the invitation and shows the institution the server resolved', async () => {
    render(<AdminInvitationPage token={TOKEN} />)

    // Nothing is trusted from the URL: the name shown comes from the server.
    expect(await screen.findByRole('heading', { name: /Join Unico University/ })).toBeDefined()
    expect(inspectSpy).toHaveBeenCalledWith(TOKEN)
    // Phase 7.15 states the binding in its own panel too, so the address
    // appears more than once by design — both must say the same thing.
    const mentions = screen.getAllByText('dean@unico.example')
    expect(mentions.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByTestId('invite-email-binding').textContent).toContain('dean@unico.example')
    // The token itself is never rendered back into the page.
    expect(document.body.textContent).not.toContain(TOKEN)
  })

  it('never lets the invited email be edited', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    // The address is informational: there is no email input to type into.
    expect(screen.queryByLabelText(/email/i)).toBeNull()
    const inputs = Array.from(document.querySelectorAll('input')) as HTMLInputElement[]
    expect(inputs.length).toBeGreaterThan(0)
    expect(inputs.every((input) => input.type !== 'email')).toBe(true)
    // Only the optional name fields and the two password fields exist.
    expect(inputs.map((input) => input.type).sort()).toEqual(['password', 'password', 'text', 'text'])
  })

  it('reports the server verification state rather than a local flag', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    // Pending acceptance: valid, not yet verified — the server says so.
    expect(screen.getByTestId('invite-verification-state').textContent).toMatch(/Invitation valid/i)
    expect(screen.getByTestId('invite-verification-state').textContent).not.toMatch(/^Email verified$/i)
  })

  it('shows the verified state the server reports', async () => {
    inspectSpy.mockResolvedValue({ ...INVITATION, email_verified: true })
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    expect(screen.getByTestId('invite-verification-state').textContent).toMatch(/Email verified/i)
  })

  it('never sends an email, verification flag or institution in the payload', async () => {
    acceptSpy.mockResolvedValue(ACCEPTED)
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    await waitFor(() => {
      expect(acceptSpy).toHaveBeenCalledWith(TOKEN, { password: PASSWORD })
    })
    const payload = acceptSpy.mock.calls[0][1] as Record<string, unknown>
    // The invitation is the ONLY source of the email and the verification
    // state, so neither can appear in the request.
    for (const forbidden of ['email', 'email_verified', 'email_verified_at', 'institution_id', 'role', 'scope']) {
      expect(payload[forbidden]).toBeUndefined()
    }
  })

  it('keeps the form usable after a rate-limit refusal', async () => {
    acceptSpy.mockRejectedValue(
      new AdminInvitationError(
        429,
        'Too many invitation requests. Please wait a moment and try again.',
        'INVITATION_RATE_LIMITED',
      ),
    )
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    // NOT terminal: the same link still works once the window passes, so the
    // form must remain available rather than stranding the invitee.
    expect(await screen.findByText(/Too many invitation requests/i)).toBeDefined()
    expect(screen.getByLabelText('Password')).toBeDefined()
    expect(screen.queryByRole('heading', { name: /cannot be used/i })).toBeNull()
  })

  it('treats a delivery failure as the operator problem, not an access change', async () => {
    // A failed email never revokes an invitation, so acceptance is unaffected.
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })
    expect(screen.getByRole('button', { name: /Create my account/i })).toBeDefined()
    expect(screen.getByLabelText('Password')).toBeDefined()
  })

  it('shows a loading state while the invitation is verified', () => {
    render(<AdminInvitationPage token={TOKEN} />)
    expect(screen.getByRole('status').textContent).toMatch(/Verifying your invitation/i)
  })
})

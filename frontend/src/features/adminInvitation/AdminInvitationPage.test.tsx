/// <reference types="vitest/globals" />
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AdminInvitationPage from './AdminInvitationPage.tsx'
import { AdminInvitationError } from '../../services/adminInvitationApi.ts'

const inspectSpy = vi.hoisted(() => vi.fn())
const acceptSpy = vi.hoisted(() => vi.fn())

vi.mock('../../services/adminInvitationApi.ts', () => ({
  AdminInvitationError: class extends Error {
    readonly status: number
    readonly code: string | null
    readonly isTerminal: boolean
    constructor(status: number, message: string, code: string | null = null) {
      super(message)
      this.status = status
      this.code = code
      this.isTerminal =
        code === 'INVITATION_EXPIRED' ||
        code === 'INVITATION_CANCELLED' ||
        code === 'INVITATION_ALREADY_ACCEPTED'
    }
  },
  inspectInvitation: inspectSpy,
  acceptInvitation: acceptSpy,
}))

const TOKEN = 'a'.repeat(64)

const INVITATION = {
  status: 'invited',
  institution_name: 'Unico University',
  institution_code: 'UNICO',
  email: 'dean@unico.example',
  expires_at: '2099-01-01T00:00:00+00:00',
  email_verified: false,
}

const ACCEPTED = {
  institution_id: 'inst-1',
  institution_name: 'Unico University',
  email: 'dean@unico.example',
  role: 'admin',
  scope: 'institution',
  message: 'Your University Admin account is ready.',
}

const PASSWORD = 'correct-horse-battery'

beforeEach(() => {
  inspectSpy.mockResolvedValue(INVITATION)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
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
    expect(screen.getByTestId('invite-email-binding').textContent).toContain(
      'dean@unico.example',
    )
    // The token itself is never rendered back into the page.
    expect(document.body.textContent).not.toContain(TOKEN)
  })

  it('never lets the invited email be edited', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    // The address is informational: there is no email input to type into.
    expect(screen.queryByLabelText(/email/i)).toBeNull()
    const inputs = Array.from(
      document.querySelectorAll('input'),
    ) as HTMLInputElement[]
    expect(inputs.length).toBeGreaterThan(0)
    expect(inputs.every((input) => input.type !== 'email')).toBe(true)
    // Only the optional name fields and the two password fields exist.
    expect(inputs.map((input) => input.type).sort()).toEqual([
      'password',
      'password',
      'text',
      'text',
    ])
  })

  it('reports the server verification state rather than a local flag', async () => {
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    // Pending acceptance: valid, not yet verified — the server says so.
    expect(screen.getByTestId('invite-verification-state').textContent).toMatch(
      /Invitation valid/i,
    )
    expect(screen.getByTestId('invite-verification-state').textContent).not.toMatch(
      /^Email verified$/i,
    )
  })

  it('shows the verified state the server reports', async () => {
    inspectSpy.mockResolvedValue({ ...INVITATION, email_verified: true })
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    expect(screen.getByTestId('invite-verification-state').textContent).toMatch(
      /Email verified/i,
    )
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
    for (const forbidden of [
      'email',
      'email_verified',
      'email_verified_at',
      'institution_id',
      'role',
      'scope',
    ]) {
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
    expect(
      await screen.findByText(/Too many invitation requests/i),
    ).toBeDefined()
    expect(screen.getByLabelText('Password')).toBeDefined()
    expect(screen.queryByRole('heading', { name: /cannot be used/i })).toBeNull()
  })

  it('treats a delivery failure as the operator problem, not an access change', async () => {
    // A failed email never revokes an invitation, so acceptance is unaffected.
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })
    expect(
      screen.getByRole('button', { name: /Create my account/i }),
    ).toBeDefined()
    expect(screen.getByLabelText('Password')).toBeDefined()
  })

  it('shows a loading state while the invitation is verified', () => {
    render(<AdminInvitationPage token={TOKEN} />)
    expect(screen.getByRole('status').textContent).toMatch(/Verifying your invitation/i)
  })

  it('offers no retry for an expired invitation', async () => {
    inspectSpy.mockRejectedValue(
      new AdminInvitationError(410, 'This invitation has expired.', 'INVITATION_EXPIRED'),
    )
    render(<AdminInvitationPage token={TOKEN} />)

    expect(
      await screen.findByRole('heading', { name: /This invitation cannot be used/i }),
    ).toBeDefined()
    expect(screen.getByText('This invitation has expired.')).toBeDefined()
    // There is no password form to retry with.
    expect(screen.queryByLabelText('Password')).toBeNull()
    expect(screen.getByRole('link', { name: /Go to admin login/i })).toBeDefined()
  })

  it('offers no retry for an already-consumed invitation', async () => {
    inspectSpy.mockRejectedValue(
      new AdminInvitationError(
        410,
        'This invitation has already been used.',
        'INVITATION_ALREADY_ACCEPTED',
      ),
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
    acceptSpy.mockRejectedValue(
      new AdminInvitationError(500, 'Please try again.', 'INVITATION_ACCEPTANCE_FAILED'),
    )
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
      new AdminInvitationError(
        410,
        'This invitation has already been used.',
        'INVITATION_ALREADY_ACCEPTED',
      ),
    )
    render(<AdminInvitationPage token={TOKEN} />)
    await screen.findByRole('heading', { name: /Join Unico University/ })

    await userEvent.type(screen.getByLabelText('Password'), PASSWORD)
    await userEvent.type(screen.getByLabelText('Confirm password'), PASSWORD)
    await userEvent.click(screen.getByRole('button', { name: /Create my account/i }))

    expect(
      await screen.findByRole('heading', { name: /This invitation cannot be used/i }),
    ).toBeDefined()
    expect(screen.queryByLabelText('Password')).toBeNull()
  })
})
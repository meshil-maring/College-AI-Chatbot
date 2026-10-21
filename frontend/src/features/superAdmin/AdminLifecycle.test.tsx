import './__tests__/AdminLifecycle.support.tsx'
import {
  cancelInvitationSpy,
  createInvitationSpy,
  PlatformInstitutionError,
  revokeAdminSpy,
  rosterSpy,
  Wrapper,
} from './__tests__/AdminLifecycle.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { AdminRoster } from '../../types/platform.ts'
import AdminRosterPanel from './AdminRosterPanel.tsx'
describe('Phase 7.14 admin roster', () => {
  it('shows accepted admins and pending invitations with their real status', async () => {
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    expect(await screen.findByText('dean@unico.example')).toBeDefined()
    expect(screen.getByText('owner@unico.example')).toBeDefined()
    expect(screen.getByText('Invited')).toBeDefined()
    // Only platform-administration fields are rendered.
    expect(document.body.textContent).not.toMatch(/password|token_hash/i)
  })

  it('explains the empty state honestly', async () => {
    rosterSpy.mockResolvedValue({
      institution_id: 'inst-1',
      admins: [],
      pending_invitations: [],
      admin_count: 0,
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    expect(await screen.findByText(/No University Admins yet/i)).toBeDefined()
  })

  it('creates an invitation from an email only and reveals the link once', async () => {
    createInvitationSpy.mockResolvedValue({
      invitation: {
        invitation_id: 'inv-2',
        institution_id: 'inst-1',
        email: 'dean@unico.example',
        status: 'invited',
        expires_at: '2099-01-01T00:00:00+00:00',
        created_at: null,
        accepted_at: null,
        cancelled_at: null,
      },
      invitation_token: 'a'.repeat(64),
      invitation_url: `/admin-invite/${'a'.repeat(64)}`,
      expires_in_hours: 24,
      email_delivery: { status: 'sent', provider: 'local', detail: null },
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: '+ Invite Admin' }))
    await userEvent.type(screen.getByLabelText('Email'), 'dean@unico.example')
    await userEvent.click(screen.getByRole('button', { name: 'Create Invitation' }))

    await waitFor(() => {
      expect(createInvitationSpy).toHaveBeenCalledWith('session-token', 'inst-1', {
        email: 'dean@unico.example',
      })
    })
    // The payload carries an email and nothing else — never a role or password.
    expect(createInvitationSpy.mock.calls[0][2]).toEqual({ email: 'dean@unico.example' })

    const link = await screen.findByTestId('invitation-link')
    expect(link.textContent).toContain('/admin-invite/')
    expect(screen.getByText(/shown only once/i)).toBeDefined()
    expect(screen.getByRole('button', { name: 'Copy link' })).toBeDefined()
  })

  it('surfaces a server-side invite error instead of inventing a link', async () => {
    createInvitationSpy.mockRejectedValue(
      new PlatformInstitutionError(409, 'An active invitation already exists for this email address'),
    )
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: '+ Invite Admin' }))
    await userEvent.type(screen.getByLabelText('Email'), 'dean@unico.example')
    await userEvent.click(screen.getByRole('button', { name: 'Create Invitation' }))

    expect(await screen.findByRole('alert')).toBeDefined()
    expect(screen.getByText(/already exists/)).toBeDefined()
    expect(screen.queryByTestId('invitation-link')).toBeNull()
  })

  it('requires an explicit confirmation before revoking', async () => {
    revokeAdminSpy.mockResolvedValue({
      institution_id: 'inst-1',
      user_id: 'user-1',
      revoked: true,
      already_revoked: false,
      message: 'ok',
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: 'Revoke' }))
    // The dialog must state what is and is not removed.
    const dialog = screen.getByRole('alertdialog')
    expect(dialog.textContent).toMatch(/only this institution's admin role/i)
    expect(dialog.textContent).toMatch(/preserved/i)
    // Nothing has been revoked yet.
    expect(revokeAdminSpy).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Revoke admin' }))
    await waitFor(() => {
      expect(revokeAdminSpy).toHaveBeenCalledWith('session-token', 'inst-1', 'user-1')
    })
  })

  it('abandons the revocation when the operator keeps the admin', async () => {
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: 'Revoke' }))
    await userEvent.click(screen.getByRole('button', { name: 'Keep admin' }))

    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(revokeAdminSpy).not.toHaveBeenCalled()
  })

  it('cancels a pending invitation through the server', async () => {
    cancelInvitationSpy.mockResolvedValue({
      invitation_id: 'inv-1',
      institution_id: 'inst-1',
      status: 'cancelled',
      already_applied: false,
      message: 'Invitation cancelled.',
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))

    await waitFor(() => {
      expect(cancelInvitationSpy).toHaveBeenCalledWith('session-token', 'inst-1', 'inv-1')
    })
  })
})

describe('Phase 7.15 invitation delivery and resend', () => {
  function rosterWith(entry: Record<string, unknown>): AdminRoster {
    return {
      institution_id: 'inst-1',
      admin_count: 0,
      admins: [],
      pending_invitations: [entry],
    } as unknown as AdminRoster
  }

  const PENDING = {
    email: 'dean@unico.example',
    kind: 'invitation',
    status: 'invited',
    user_id: null,
    invitation_id: 'inv-1',
    institution_id: 'inst-1',
    expires_at: '2099-01-01T00:00:00+00:00',
    email_delivery_status: 'sent',
    email_delivery_attempts: 1,
    email_verified: false,
    resend_count: 0,
  }

  it('shows the invitation email state next to the lifecycle state', async () => {
    rosterSpy.mockResolvedValue(
      rosterWith({
        ...PENDING,
        email_delivery_status: 'failed',
        email_delivery_attempts: 2,
        resend_count: 1,
      }),
    )
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    expect(await screen.findByText('Invited')).toBeDefined()
    // A failed send is stated plainly, with the attempt count, so the operator
    // knows to resend rather than assume the person received the link.
    expect(screen.getByText(/Email not sent \(2 attempts\)/)).toBeDefined()
    expect(screen.getByText(/Resent 1×/)).toBeDefined()
  })

  it('shows an expired invitation as resendable but not cancellable', async () => {
    rosterSpy.mockResolvedValue(rosterWith({ ...PENDING, status: 'expired', expires_at: '2000-01-01T00:00:00+00:00' }))
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    expect(await screen.findByText('Expired')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Resend' })).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull()
  })

  it('never offers a resend for a cancelled invitation', async () => {
    rosterSpy.mockResolvedValue(rosterWith({ ...PENDING, status: 'cancelled', expires_at: null }))
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    expect(await screen.findByText('Cancelled')).toBeDefined()
    // Reissuing would silently undo an explicit operator decision.
    expect(screen.queryByRole('button', { name: 'Resend' })).toBeNull()
    expect(screen.getByText('No action')).toBeDefined()
  })
})

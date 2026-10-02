/// <reference types="vitest/globals" />
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import AdminRosterPanel from './AdminRosterPanel.tsx'
import PlatformAuditView from './PlatformAuditView.tsx'
import type { AdminRoster, PlatformAuditPage } from '../../types/platform.ts'

const rosterSpy = vi.hoisted(() => vi.fn())
const createInvitationSpy = vi.hoisted(() => vi.fn())
const cancelInvitationSpy = vi.hoisted(() => vi.fn())
const resendInvitationSpy = vi.hoisted(() => vi.fn())
const revokeAdminSpy = vi.hoisted(() => vi.fn())
const auditSpy = vi.hoisted(() => vi.fn())

const PlatformInstitutionError = vi.hoisted(
  () =>
    class extends Error {
      readonly status: number
      constructor(status: number, message: string) {
        super(message)
        this.status = status
      }
    },
)

vi.mock('../../services/platformInstitutionsApi.ts', () => ({
  PlatformInstitutionError,
  getAdminRoster: rosterSpy,
  createInvitation: createInvitationSpy,
  cancelInvitation: cancelInvitationSpy,
  resendInvitation: resendInvitationSpy,
  revokeInstitutionAdmin: revokeAdminSpy,
  listPlatformAudit: auditSpy,
}))

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'session-token' }),
}))

function Wrapper({ children }: { children: ReactNode }) {
  return <>{children}</>
}

const ROSTER: AdminRoster = {
  institution_id: 'inst-1',
  admin_count: 1,
  admins: [
    {
      email: 'dean@unico.example',
      kind: 'admin',
      status: 'active',
      user_id: 'user-1',
      invitation_id: null,
      institution_id: 'inst-1',
      expires_at: null,
    },
  ],
  pending_invitations: [
    {
      email: 'owner@unico.example',
      kind: 'invitation',
      status: 'invited',
      user_id: null,
      invitation_id: 'inv-1',
      institution_id: 'inst-1',
      email_delivery_status: 'sent',
      email_delivery_attempts: 1,
      email_verified: false,
      resend_count: 0,
      expires_at: '2099-01-01T00:00:00+00:00',
    },
  ],
}

const AUDIT_PAGE: PlatformAuditPage = {
  total: 1,
  limit: 25,
  offset: 0,
  entries: [
    {
      audit_id: 'audit-1',
      actor_user_id: 'user-9',
      actor_email: 'root@platform.test',
      action: 'institution_admin_invited',
      institution_id: 'inst-1',
      institution_name: 'Unico University',
      target_user_id: null,
      result: 'success',
      details: {},
      performed_at: '2026-10-01T00:00:00+00:00',
    },
  ],
}

beforeEach(() => {
  rosterSpy.mockResolvedValue(ROSTER)
  auditSpy.mockResolvedValue(AUDIT_PAGE)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
describe('Phase 7.14 admin roster', () => {
  it('shows accepted admins and pending invitations with their real status', async () => {
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    render(
      <AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />,
      { wrapper: Wrapper },
    )

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
    rosterSpy.mockResolvedValue(
      rosterWith({ ...PENDING, status: 'expired', expires_at: '2000-01-01T00:00:00+00:00' }),
    )
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    expect(await screen.findByText('Expired')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Resend' })).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull()
  })

  it('never offers a resend for a cancelled invitation', async () => {
    rosterSpy.mockResolvedValue(
      rosterWith({ ...PENDING, status: 'cancelled', expires_at: null }),
    )
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    expect(await screen.findByText('Cancelled')).toBeDefined()
    // Reissuing would silently undo an explicit operator decision.
    expect(screen.queryByRole('button', { name: 'Resend' })).toBeNull()
    expect(screen.getByText('No action')).toBeDefined()
  })

it('resends through the server and reveals the new one-time link', async () => {
    resendInvitationSpy.mockResolvedValue({
      invitation: { ...PENDING, resend_count: 1 },
      invitation_token: 'b'.repeat(64),
      invitation_url: `/admin-invite/${'b'.repeat(64)}`,
      expires_in_hours: 24,
      email_delivery: { status: 'sent', provider: 'local', detail: null },
      previous_token_invalidated: true,
      message: 'A new invitation link has been issued and emailed.',
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Resend' }))
    // The confirmation explains that the previous link dies.
    const dialog = await screen.findByRole('alertdialog')
    expect(dialog.textContent).toMatch(/previous link stops working/i)

    await userEvent.click(screen.getByRole('button', { name: 'Send new link' }))
    await waitFor(() => {
      expect(resendInvitationSpy).toHaveBeenCalledWith('session-token', 'inst-1', 'inv-1')
    })

    const link = await screen.findByTestId('invitation-link')
    expect(link.textContent).toContain('/admin-invite/')
    // The revealed link is the NEW one, and it is shown only once.
    expect(link.textContent).not.toContain('a'.repeat(64))
    expect(screen.getByText(/shown only once/i)).toBeDefined()
  })

  it('abandons a resend when the operator keeps the current link', async () => {
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Resend' }))
    await userEvent.click(screen.getByRole('button', { name: 'Keep current link' }))

    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(resendInvitationSpy).not.toHaveBeenCalled()
  })

  it('reports a rate-limit refusal without pretending the resend happened', async () => {
    resendInvitationSpy.mockRejectedValue(
      new PlatformInstitutionError(
        429,
        'Too many invitation requests. Please wait a moment and try again.',
      ),
    )
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Resend' }))
    await userEvent.click(screen.getByRole('button', { name: 'Send new link' }))

    expect(await screen.findByRole('alert')).toBeDefined()
    expect(screen.getByText(/Too many invitation requests/i)).toBeDefined()
    // No link is revealed, because no new token was issued.
    expect(screen.queryByTestId('invitation-link')).toBeNull()
  })

  it('says plainly when the email could not be sent', async () => {
    resendInvitationSpy.mockResolvedValue({
      invitation: { ...PENDING, email_delivery_status: 'failed' },
      invitation_token: 'b'.repeat(64),
      invitation_url: `/admin-invite/${'b'.repeat(64)}`,
      expires_in_hours: 24,
      email_delivery: {
        status: 'failed',
        provider: 'production',
        detail: 'DELIVERY_TEMPORARY_FAILURE',
      },
      previous_token_invalidated: true,
      message: 'A new invitation link was issued, but the email could not be sent.',
    })
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Resend' }))
    await userEvent.click(screen.getByRole('button', { name: 'Send new link' }))

    expect(await screen.findByText(/Invitation could not be delivered/i)).toBeDefined()
    // The failure is never dressed up as success.
    expect(screen.queryByText(/emailed to the invited address/i)).toBeNull()
  })

  it('never renders a token or credential in the roster', async () => {
    render(<AdminRosterPanel institutionId="inst-1" institutionCode="UNICO" />, {
      wrapper: Wrapper,
    })
    await screen.findByText('owner@unico.example')
    expect(document.body.textContent).not.toMatch(/password|token_hash|api_key/i)
  })
})

describe('Phase 7.14 platform audit view', () => {
  it('renders the audit timeline read-only', async () => {
    render(<PlatformAuditView />, { wrapper: Wrapper })

    expect(await screen.findByText('Invited admin')).toBeDefined()
    expect(screen.getByText('root@platform.test')).toBeDefined()
    expect(screen.getByText('Unico University')).toBeDefined()
    // There is NO mutation control anywhere in this view.
    const labels = screen.getAllByRole('button').map((b) => b.textContent ?? '')
    expect(labels.some((l) => /delete|remove|edit|create/i.test(l))).toBe(false)
  })

  it('filters by action through a server-side query parameter', async () => {
    render(<PlatformAuditView />, { wrapper: Wrapper })
    await screen.findByText('Invited admin')

    await userEvent.selectOptions(
      screen.getByLabelText('Filter by action'),
      'institution_admin_revoked',
    )

    await waitFor(() => {
      expect(auditSpy).toHaveBeenLastCalledWith('session-token', {
        limit: 25,
        offset: 0,
        action: 'institution_admin_revoked',
      })
    })
  })

  it('shows an honest empty state', async () => {
    auditSpy.mockResolvedValue({ total: 0, limit: 25, offset: 0, entries: [] })
    render(<PlatformAuditView />, { wrapper: Wrapper })

    expect(await screen.findByText(/No audit records match/i)).toBeDefined()
  })

  it('surfaces an authorization error instead of pretending the ledger is empty', async () => {
    auditSpy.mockRejectedValue(
      new PlatformInstitutionError(
        403,
        'You do not have permission to perform this action',
      ),
    )
    render(<PlatformAuditView />, { wrapper: Wrapper })

    expect(await screen.findByRole('alert')).toBeDefined()
    expect(screen.getByText(/do not have permission/i)).toBeDefined()
  })
})

import './__tests__/AdminLifecycle.support.tsx'
import {
  auditSpy,
  PlatformInstitutionError,
  resendInvitationSpy,
  Wrapper,
} from './__tests__/AdminLifecycle.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { AdminRoster } from '../../types/platform.ts'
import AdminRosterPanel from './AdminRosterPanel.tsx'
import PlatformAuditView from './PlatformAuditView.tsx'
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
      new PlatformInstitutionError(429, 'Too many invitation requests. Please wait a moment and try again.'),
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

    await userEvent.selectOptions(screen.getByLabelText('Filter by action'), 'institution_admin_revoked')

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
    auditSpy.mockRejectedValue(new PlatformInstitutionError(403, 'You do not have permission to perform this action'))
    render(<PlatformAuditView />, { wrapper: Wrapper })

    expect(await screen.findByRole('alert')).toBeDefined()
    expect(screen.getByText(/do not have permission/i)).toBeDefined()
  })
})

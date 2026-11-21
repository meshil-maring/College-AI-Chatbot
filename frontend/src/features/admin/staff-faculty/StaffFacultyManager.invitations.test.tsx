import './__tests__/StaffFacultyManager.support.ts'
import { CSE, MECH } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'
import type { MemberInvitation } from '../../../types/admin.ts'

function invitation(changes: Partial<MemberInvitation> = {}): MemberInvitation {
  return {
    invitation_id: '50000000-0000-0000-0000-000000000001',
    email: 'ada@example.com',
    full_name: 'Ada Lovelace',
    role: 'faculty',
    department_id: CSE.department_id,
    status: 'invited',
    expires_at: '2099-01-01T00:00:00Z',
    created_at: '2026-11-21T00:00:00Z',
    email_delivery_status: 'sent',
    resend_count: 0,
    last_sent_at: null,
    ...changes,
  }
}

async function openDialog() {
  fireEvent.click(await screen.findByRole('button', { name: 'Add member' }))
  return screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
}

describe('Staff and Faculty Management — invitations', () => {
  it('invites a new Faculty member into the chosen department', async () => {
    vi.mocked(api.createMembershipInvitation).mockResolvedValue({
      invitation: invitation(),
      email_delivery: { status: 'pending', provider: 'outbox' },
      expires_in_hours: 24,
      message: 'Invitation sent to ada@example.com. They join as Faculty (Teacher) once they accept.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    const dialog = await openDialog()
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Full name/ }), {
      target: { value: ' Ada Lovelace ' },
    })
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Email/ }), { target: { value: 'Ada@Example.com' } })
    fireEvent.change(within(dialog).getByRole('combobox', { name: /Department/ }), {
      target: { value: MECH.department_id },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() =>
      expect(api.createMembershipInvitation).toHaveBeenCalledWith('jwt', {
        full_name: 'Ada Lovelace',
        email: 'ada@example.com',
        role: 'faculty',
        department_id: MECH.department_id,
      }),
    )
    expect(await screen.findByText(/Invitation sent to ada@example.com/)).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).toBeNull()
    // After sending, the Pending invitations page opens so the new invitation is visible.
    expect(screen.getByRole('region', { name: 'Pending invitations' })).toBeInTheDocument()
  })

  it('explains missing fields before sending anything', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('radio', { name: /Staff/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    expect(within(dialog).getByText('Enter their name.')).toBeInTheDocument()
    expect(within(dialog).getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(within(dialog).getByText('Choose a department.')).toBeInTheDocument()
    expect(within(dialog).getByRole('textbox', { name: /Full name/ })).toHaveAttribute('aria-invalid', 'true')
    expect(api.createMembershipInvitation).not.toHaveBeenCalled()
  })

  it('keeps the form open and shows why the server refused', async () => {
    vi.mocked(api.createMembershipInvitation).mockRejectedValue(
      new Error('This email already belongs to a member of your institution.'),
    )
    render(<StaffFacultyManager accessToken="jwt" />)
    const dialog = await openDialog()
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Full name/ }), { target: { value: 'Sam' } })
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Email/ }), { target: { value: 'sam@example.com' } })
    fireEvent.change(within(dialog).getByRole('combobox', { name: /Department/ }), {
      target: { value: CSE.department_id },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('already belongs to a member')
    expect(within(dialog).getByRole('textbox', { name: /Email/ })).toHaveValue('sam@example.com')
  })

  it('lists pending invitations with resend and cancel', async () => {
    vi.mocked(api.listMembershipInvitations).mockResolvedValue({ invitations: [invitation()], total: 1 })
    vi.mocked(api.resendMembershipInvitation).mockResolvedValue({})
    vi.mocked(api.cancelMembershipInvitation).mockResolvedValue({
      invitation_id: invitation().invitation_id,
      already_applied: false,
      message: 'Invitation cancelled. The link no longer works.',
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="invitations" />)
    const section = await screen.findByRole('region', { name: 'Pending invitations' })
    expect(await within(section).findByText('Ada Lovelace')).toBeInTheDocument()
    expect(within(section).getByText('Computer Science')).toBeInTheDocument()
    expect(within(section).getByText('Email sent')).toBeInTheDocument()
    fireEvent.click(within(section).getByRole('button', { name: 'Resend invitation to Ada Lovelace' }))
    await waitFor(() => expect(api.resendMembershipInvitation).toHaveBeenCalledWith('jwt', invitation().invitation_id))
    expect(await within(section).findByText(/A new invitation link was sent/)).toBeInTheDocument()
    fireEvent.click(within(section).getByRole('button', { name: 'Cancel invitation for Ada Lovelace' }))
    expect(window.confirm).toHaveBeenCalledWith('Cancel the invitation for Ada Lovelace?')
    await waitFor(() => expect(api.cancelMembershipInvitation).toHaveBeenCalledWith('jwt', invitation().invitation_id))
    expect(await within(section).findByText('Invitation cancelled. The link no longer works.')).toBeInTheDocument()
  })

  it('offers to invite again with the same details once a link expires', async () => {
    vi.mocked(api.listMembershipInvitations).mockResolvedValue({
      invitations: [invitation({ status: 'expired', role: 'staff' })],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="invitations" />)
    const section = await screen.findByRole('region', { name: 'Pending invitations' })
    expect(within(section).queryByRole('button', { name: /Resend/ })).toBeNull()
    fireEvent.click(await within(section).findByRole('button', { name: 'Invite Ada Lovelace again' }))
    const dialog = screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
    expect(within(dialog).getByRole('textbox', { name: /Email/ })).toHaveValue('ada@example.com')
    expect(within(dialog).getByRole('radio', { name: /Staff/ })).toBeChecked()
    expect(within(dialog).getByRole('combobox', { name: /Department/ })).toHaveValue(CSE.department_id)
  })
})

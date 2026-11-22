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

function type(dialog: HTMLElement, role: 'textbox' | 'combobox', name: RegExp, value: string) {
  fireEvent.change(within(dialog).getByRole(role, { name }), { target: { value } })
}

async function openDialog() {
  fireEvent.click(await screen.findByRole('button', { name: 'Add member' }))
  return screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
}

describe('Staff and Faculty Management — invitations', () => {
  it('invites a new Faculty member through basic details, role details and review', async () => {
    vi.mocked(api.createMembershipInvitation).mockResolvedValue({
      invitation: invitation(),
      email_delivery: { status: 'pending', provider: 'outbox' },
      expires_in_hours: 24,
      message: 'Invitation sent to ada@example.com. They join as Faculty (Teacher) once they accept.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    const dialog = await openDialog()
    type(dialog, 'textbox', /Full name/, ' Ada Lovelace ')
    type(dialog, 'textbox', /Email/, 'Ada@Example.com')
    type(dialog, 'textbox', /Employee ID/, 'EMP-001')
    type(dialog, 'textbox', /Designation/, 'Assistant Professor')
    fireEvent.change(within(dialog).getByLabelText(/Joining date/), { target: { value: '2026-07-01' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    type(dialog, 'combobox', /Primary department/, MECH.department_id)
    fireEvent.click(within(dialog).getByRole('checkbox', { name: 'Computer Science' }))
    // Employment starts on the joining date unless changed.
    expect(within(dialog).getByLabelText(/Employment start date/)).toHaveValue('2026-07-01')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByText('Invitation pending')).toBeInTheDocument()
    expect(within(dialog).getByText('Mechanical')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() =>
      expect(api.createMembershipInvitation).toHaveBeenCalledWith('jwt', {
        full_name: 'Ada Lovelace',
        email: 'ada@example.com',
        role: 'faculty',
        department_id: MECH.department_id,
        additional_department_ids: [CSE.department_id],
        profile: {
          common: {
            employee_id: 'EMP-001',
            phone: null,
            designation: 'Assistant Professor',
            joining_date: '2026-07-01',
          },
          faculty: {
            employment_type: 'permanent',
            employment_start_date: '2026-07-01',
            contract_end_date: null,
            qualification: null,
            specialization: null,
            experience_years: null,
          },
        },
      }),
    )
    expect(await screen.findByText(/Invitation sent to ada@example.com/)).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).toBeNull()
    // After sending, the Pending invitations page opens so the new invitation is visible.
    expect(screen.getByRole('region', { name: 'Pending invitations' })).toBeInTheDocument()
  })

  it('explains missing basic details before moving on', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByText('Enter their name.')).toBeInTheDocument()
    expect(within(dialog).getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(within(dialog).getByText('Enter the designation.')).toBeInTheDocument()
    expect(within(dialog).getByText('Choose the joining date.')).toBeInTheDocument()
    expect(within(dialog).getByRole('textbox', { name: /Full name/ })).toHaveAttribute('aria-invalid', 'true')
    expect(within(dialog).getByText(/Step 1 of 3/)).toBeInTheDocument()
    expect(api.createMembershipInvitation).not.toHaveBeenCalled()
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
    vi.mocked(api.resendMembershipInvitation).mockResolvedValueOnce({
      invitation_id: invitation().invitation_id,
      email_delivery: { status: 'failed', provider: 'test' },
      expires_in_hours: 72,
      message: 'A new invitation link was issued, but the email could not be sent. Try resending again.',
    })
    fireEvent.click(within(section).getByRole('button', { name: 'Resend invitation to Ada Lovelace' }))
    expect(await within(section).findByText(/the email could not be sent/)).toBeInTheDocument()
    fireEvent.click(within(section).getByRole('button', { name: 'Cancel invitation for Ada Lovelace' }))
    expect(window.confirm).toHaveBeenCalledWith('Cancel the invitation for Ada Lovelace?')
    await waitFor(() => expect(api.cancelMembershipInvitation).toHaveBeenCalledWith('jwt', invitation().invitation_id))
    expect(await within(section).findByText('Invitation cancelled. The link no longer works.')).toBeInTheDocument()
  })

  it('offers to invite again with the same details once a link expires', async () => {
    vi.mocked(api.listMembershipInvitations).mockResolvedValue({
      invitations: [invitation({ status: 'expired', role: 'staff', employee_id: 'EMP-001' })],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="invitations" />)
    const section = await screen.findByRole('region', { name: 'Pending invitations' })
    expect(within(section).queryByRole('button', { name: /Resend/ })).toBeNull()
    fireEvent.click(await within(section).findByRole('button', { name: 'Invite Ada Lovelace again' }))
    const dialog = screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
    expect(within(dialog).getByRole('textbox', { name: /Email/ })).toHaveValue('ada@example.com')
    expect(within(dialog).getByRole('textbox', { name: /Employee ID/ })).toHaveValue('EMP-001')
    expect(within(dialog).getByRole('radio', { name: /Staff/ })).toBeChecked()
    fireEvent.change(within(dialog).getByLabelText(/Joining date/), { target: { value: '2026-07-01' } })
    type(dialog, 'textbox', /Designation/, 'Office Assistant')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByRole('combobox', { name: /Primary department/ })).toHaveValue(CSE.department_id)
  })
})

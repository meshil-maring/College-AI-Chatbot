import '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'
import type { InstitutionAdmin, InstitutionAdminList } from '../../../../types/admin/administrators.ts'

const OWNER: InstitutionAdmin = {
  user_id: 'owner-1',
  name: 'Olive Owner',
  email: 'olive@example.com',
  status: 'active',
  assigned_at: null,
  is_owner: true,
  access_areas: null,
  profile: null,
}
const ABE: InstitutionAdmin = {
  ...OWNER,
  user_id: 'admin-2',
  name: 'Abe Admin',
  email: 'abe@example.com',
  is_owner: false,
  profile: { employee_id: 'ADM-2', phone: null, designation: 'Registrar', joining_date: '2026-01-05' },
}

function listing(viewer: string, changes: Partial<InstitutionAdminList> = {}): InstitutionAdminList {
  return {
    owner_user_id: 'owner-1',
    viewer_is_owner: viewer === 'owner-1',
    viewer_user_id: viewer,
    administrators: [OWNER, ABE],
    invitations: [],
    access_area_options: [],
    ...changes,
  }
}

async function openPage(data: InstitutionAdminList) {
  vi.mocked(api.listInstitutionAdmins).mockResolvedValue(data)
  render(<StaffFacultyManager accessToken="jwt" defaultPage="administrators" />)
  const region = await screen.findByRole('region', { name: 'Administrators' })
  await within(region).findByText('Abe Admin')
  return region
}

describe('Administrator profiles', () => {
  it('shows profiles, flags missing ones, and lets an administrator edit only their own', async () => {
    const region = await openPage(listing('admin-2'))
    expect(within(region).getByText('Registrar · ADM-2')).toBeInTheDocument()
    expect(within(region).getByText('Profile incomplete')).toBeInTheDocument()
    expect(within(region).queryByRole('button', { name: 'Edit profile of Olive Owner' })).toBeNull()
    expect(within(region).getByRole('button', { name: 'Edit profile of Abe Admin' })).toBeEnabled()
  })

  it('checks the fields, then saves the administrator’s own profile', async () => {
    vi.mocked(api.saveInstitutionAdminProfile).mockResolvedValue({ message: 'Profile saved.', already_applied: false })
    const region = await openPage(listing('admin-2'))
    fireEvent.click(within(region).getByRole('button', { name: 'Edit profile of Abe Admin' }))
    const editor = within(region).getByRole('region', { name: 'Profile of Abe Admin' })
    expect(within(editor).getByLabelText('Employee ID')).toHaveValue('ADM-2')
    fireEvent.change(within(editor).getByLabelText('Employee ID'), { target: { value: 'ADM 2' } })
    fireEvent.change(within(editor).getByLabelText(/Phone/), { target: { value: '  +91 98765  43210 ' } })
    fireEvent.click(within(editor).getByRole('button', { name: 'Save profile' }))
    expect(within(editor).getByText(/Use up to 40 letters/)).toBeInTheDocument()
    expect(api.saveInstitutionAdminProfile).not.toHaveBeenCalled()
    fireEvent.change(within(editor).getByLabelText('Employee ID'), { target: { value: 'ADM-2' } })
    fireEvent.click(within(editor).getByRole('button', { name: 'Save profile' }))
    await waitFor(() =>
      expect(api.saveInstitutionAdminProfile).toHaveBeenCalledWith('jwt', 'admin-2', {
        employee_id: 'ADM-2',
        phone: '+91 98765 43210',
        designation: 'Registrar',
        joining_date: '2026-01-05',
      }),
    )
    expect(await screen.findByText('Profile saved.')).toBeInTheDocument()
  })

  it('lets the Owner add employee details to an invitation', async () => {
    vi.mocked(api.inviteInstitutionAdmin).mockResolvedValue({ message: 'Invitation sent.', already_applied: false })
    await openPage(listing('owner-1'))
    const form = screen.getByRole('form', { name: 'Invite an administrator' })
    fireEvent.change(within(form).getByLabelText(/^Email/), { target: { value: 'pro@example.com' } })
    fireEvent.click(within(form).getByRole('checkbox', { name: /Add employee details now/ }))
    fireEvent.change(within(form).getByLabelText('Employee ID'), { target: { value: 'ADM-7' } })
    fireEvent.change(within(form).getByLabelText('Designation'), { target: { value: 'Registrar' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Send invitation' }))
    expect(within(form).getByText('Choose the joining date.')).toBeInTheDocument()
    fireEvent.change(within(form).getByLabelText('Joining date'), { target: { value: '2026-02-01' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() =>
      expect(api.inviteInstitutionAdmin).toHaveBeenCalledWith('jwt', {
        email: 'pro@example.com',
        full_name: null,
        access_areas: null,
        profile: { employee_id: 'ADM-7', phone: null, designation: 'Registrar', joining_date: '2026-02-01' },
      }),
    )
  })

  it('lets the Owner resend a pending invitation', async () => {
    vi.mocked(api.resendInstitutionAdminInvitation).mockResolvedValue({
      message: 'A new invitation email was sent.',
      already_applied: false,
    })
    await openPage(
      listing('owner-1', {
        invitations: [
          {
            invitation_id: 'i-1',
            email: 'late@example.com',
            full_name: null,
            expires_at: null,
            created_at: null,
            email_delivery_status: 'sent',
            access_areas: null,
            profile: null,
          },
        ],
      }),
    )
    const pending = screen.getByRole('region', { name: 'Pending administrator invitations' })
    fireEvent.click(within(pending).getByRole('button', { name: 'Resend the invitation to late@example.com' }))
    await waitFor(() => expect(api.resendInstitutionAdminInvitation).toHaveBeenCalledWith('jwt', 'i-1'))
    expect(await screen.findByText('A new invitation email was sent.')).toBeInTheDocument()
  })
})

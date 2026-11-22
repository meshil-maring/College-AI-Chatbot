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
}
const LIMITED: InstitutionAdmin = {
  ...OWNER,
  user_id: 'admin-2',
  name: 'Abe Admin',
  email: 'abe@example.com',
  is_owner: false,
  access_areas: ['students', 'content'],
}

function listing(viewerIsOwner: boolean, admins: InstitutionAdmin[] = [OWNER, LIMITED]): InstitutionAdminList {
  return {
    owner_user_id: 'owner-1',
    viewer_is_owner: viewerIsOwner,
    administrators: admins,
    invitations: [],
    access_area_options: [
      'staff_faculty',
      'students',
      'academic_setup',
      'content',
      'staff_permissions',
      'settings_audit',
    ],
  }
}

async function openPage(data: InstitutionAdminList) {
  vi.mocked(api.listInstitutionAdmins).mockResolvedValue(data)
  render(<StaffFacultyManager accessToken="jwt" defaultPage="administrators" />)
  const region = await screen.findByRole('region', { name: 'Administrators' })
  await within(region).findByText('Abe Admin')
  return region
}

describe('Administrator access areas', () => {
  it('shows each administrator’s access and keeps editing to the Owner', async () => {
    const region = await openPage(listing(false))
    expect(within(region).getByText('Full access (Owner)')).toBeInTheDocument()
    expect(within(region).getByText('Students, Content')).toBeInTheDocument()
    expect(within(region).queryByRole('button', { name: /Edit access/ })).toBeNull()
  })

  it('never offers the Owner a limit on their own access', async () => {
    const region = await openPage(listing(true))
    expect(within(region).queryByRole('button', { name: 'Edit access for Olive Owner' })).toBeNull()
    expect(within(region).getByRole('button', { name: 'Edit access for Abe Admin' })).toBeEnabled()
  })

  it('lets the Owner change access, and ticking everything gives full access', async () => {
    vi.mocked(api.setInstitutionAdminAccess).mockResolvedValue({
      message: 'Access updated. Changes apply on their next request.',
      already_applied: false,
    })
    const region = await openPage(listing(true))
    fireEvent.click(within(region).getByRole('button', { name: 'Edit access for Abe Admin' }))
    const editor = within(region).getByRole('group', { name: 'Access for Abe Admin' })
    expect(within(editor).getByRole('checkbox', { name: 'Students' })).toBeChecked()
    expect(within(editor).getByRole('checkbox', { name: 'Academic setup' })).not.toBeChecked()
    fireEvent.click(within(editor).getByRole('checkbox', { name: 'Content' }))
    fireEvent.click(within(editor).getByRole('checkbox', { name: 'Staff and Faculty' }))
    fireEvent.click(within(region).getByRole('button', { name: 'Save access' }))
    await waitFor(() =>
      expect(api.setInstitutionAdminAccess).toHaveBeenCalledWith('jwt', 'admin-2', ['staff_faculty', 'students']),
    )
    expect(await screen.findByText(/Access updated/)).toBeInTheDocument()
    expect(within(region).queryByRole('group', { name: 'Access for Abe Admin' })).toBeNull()

    fireEvent.click(within(region).getByRole('button', { name: 'Edit access for Abe Admin' }))
    const again = within(region).getByRole('group', { name: 'Access for Abe Admin' })
    for (const name of ['Staff and Faculty', 'Academic setup', 'Staff permissions', 'Settings and audit']) {
      fireEvent.click(within(again).getByRole('checkbox', { name }))
    }
    fireEvent.click(within(region).getByRole('button', { name: 'Save access' }))
    await waitFor(() => expect(api.setInstitutionAdminAccess).toHaveBeenLastCalledWith('jwt', 'admin-2', null))
  })

  it('invites an administrator with limited access', async () => {
    vi.mocked(api.inviteInstitutionAdmin).mockResolvedValue({ message: 'Invitation sent.', already_applied: false })
    await openPage(listing(true))
    const form = screen.getByRole('form', { name: 'Invite an administrator' })
    fireEvent.change(within(form).getByLabelText(/^Email/), { target: { value: 'lim@example.com' } })
    const access = within(form).getByRole('group', { name: 'Access' })
    for (const name of ['Staff and Faculty', 'Students', 'Academic setup', 'Staff permissions', 'Settings and audit']) {
      fireEvent.click(within(access).getByRole('checkbox', { name }))
    }
    fireEvent.click(within(form).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() =>
      expect(api.inviteInstitutionAdmin).toHaveBeenCalledWith('jwt', {
        email: 'lim@example.com',
        full_name: null,
        access_areas: ['content'],
        profile: null,
      }),
    )
  })
})

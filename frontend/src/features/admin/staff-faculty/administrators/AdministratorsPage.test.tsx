import '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'
import type { InstitutionAdminList } from '../../../../types/admin/administrators.ts'

function listing(viewerIsOwner: boolean, changes: Partial<InstitutionAdminList> = {}): InstitutionAdminList {
  return {
    owner_user_id: 'owner-1',
    viewer_is_owner: viewerIsOwner,
    administrators: [
      {
        user_id: 'owner-1',
        name: 'Olive Owner',
        email: 'olive@example.com',
        status: 'active',
        assigned_at: null,
        is_owner: true,
      },
      {
        user_id: 'admin-2',
        name: 'Abe Admin',
        email: 'abe@example.com',
        status: 'active',
        assigned_at: null,
        is_owner: false,
      },
    ],
    invitations: [],
    ...changes,
  }
}

async function openPage(data: InstitutionAdminList) {
  vi.mocked(api.listInstitutionAdmins).mockResolvedValue(data)
  render(<StaffFacultyManager accessToken="jwt" defaultPage="administrators" />)
  return screen.findByRole('region', { name: 'Administrators' })
}

describe('Staff and Faculty — Administrators', () => {
  it('shows other administrators a read-only list', async () => {
    const list = await openPage(listing(false))
    expect(await within(list).findByText('Olive Owner')).toBeInTheDocument()
    expect(within(list).getByText('Owner')).toBeInTheDocument()
    expect(screen.getByText('Only the institution Owner can invite or remove administrators.')).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Invite an administrator' })).toBeNull()
    expect(within(list).queryByRole('button', { name: /Remove/ })).toBeNull()
  })

  it('lets the Owner invite an administrator', async () => {
    vi.mocked(api.inviteInstitutionAdmin).mockResolvedValue({
      message: 'Invitation sent to new@example.com. They become an administrator once they accept.',
      already_applied: false,
    })
    await openPage(listing(true))
    const form = await screen.findByRole('form', { name: 'Invite an administrator' })
    fireEvent.click(within(form).getByRole('button', { name: 'Send invitation' }))
    expect(within(form).getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(api.inviteInstitutionAdmin).not.toHaveBeenCalled()
    fireEvent.change(within(form).getByLabelText(/^Email/), { target: { value: ' New@Example.com ' } })
    fireEvent.change(within(form).getByLabelText(/Full name/), { target: { value: ' Nia New ' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() =>
      expect(api.inviteInstitutionAdmin).toHaveBeenCalledWith('jwt', {
        email: 'new@example.com',
        full_name: 'Nia New',
      }),
    )
    expect(await screen.findByText(/They become an administrator once they accept/)).toBeInTheDocument()
    expect(within(form).getByLabelText(/^Email/)).toHaveValue('')
  })

  it('lets the Owner remove an administrator or hand over ownership, never themselves', async () => {
    vi.mocked(api.revokeInstitutionAdmin).mockResolvedValue({
      message: 'Administrator access removed.',
      already_applied: false,
    })
    vi.mocked(api.transferInstitutionOwnership).mockResolvedValue({
      message: 'Ownership transferred.',
      already_applied: false,
    })
    const list = await openPage(listing(true))
    await within(list).findByText('Abe Admin')
    expect(within(list).queryByRole('button', { name: 'Remove Olive Owner as administrator' })).toBeNull()
    fireEvent.click(within(list).getByRole('button', { name: 'Remove Abe Admin as administrator' }))
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("Remove Abe Admin's administrator access"))
    await waitFor(() => expect(api.revokeInstitutionAdmin).toHaveBeenCalledWith('jwt', 'admin-2'))
    fireEvent.click(await within(list).findByRole('button', { name: 'Make Abe Admin the Owner' }))
    await waitFor(() => expect(api.transferInstitutionOwnership).toHaveBeenCalledWith('jwt', 'admin-2'))
  })

  it('shows refusals and lets the Owner cancel pending invitations', async () => {
    vi.mocked(api.cancelInstitutionAdminInvitation).mockRejectedValue(
      new Error('Only the institution Owner can manage administrators.'),
    )
    await openPage(
      listing(true, {
        invitations: [
          {
            invitation_id: 'i-1',
            email: 'late@example.com',
            full_name: null,
            expires_at: null,
            created_at: null,
            email_delivery_status: 'sent',
          },
        ],
      }),
    )
    const pending = await screen.findByRole('region', { name: 'Pending administrator invitations' })
    fireEvent.click(within(pending).getByRole('button', { name: 'Cancel the invitation for late@example.com' }))
    await waitFor(() => expect(api.cancelInstitutionAdminInvitation).toHaveBeenCalledWith('jwt', 'i-1'))
    expect(await screen.findByText('Only the institution Owner can manage administrators.')).toBeInTheDocument()
  })
})

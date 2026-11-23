import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StaffPermissionManager from './StaffPermissionManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'

vi.mock('../../../services/admin/adminApi.ts')

const state = {
  user_id: 'staff-1',
  institution_id: 'institution-1',
  permissions: [
    { code: 'students.read', inherited: true, direct_grant_id: null },
    { code: 'attendance.manage', inherited: false, direct_grant_id: 'grant-1' },
  ],
  delegable_permissions: ['attendance.manage', 'documents.read'],
}

async function startEditing() {
  const edit = await screen.findByRole('button', { name: 'Edit permissions' })
  await waitFor(() => expect(edit).toBeEnabled())
  fireEvent.click(edit)
}

describe('StaffPermissionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [
        {
          user_id: 'staff-1',
          email: 'staff@example.test',
          name: 'Staff One',
          role: 'staff',
          status: 'active',
        },
      ],
      total: 1,
    })
    vi.mocked(api.getDelegableStaffPermissions).mockResolvedValue(['attendance.manage', 'documents.read'])
    vi.mocked(api.getStaffPermissions).mockResolvedValue(state)
  })

  it('shows inherited grants as read-only and revokes a direct grant when it is unticked', async () => {
    vi.mocked(api.changeStaffPermissions).mockResolvedValue({ changed: 1, permissions: state })
    render(<StaffPermissionManager accessToken="jwt" />)
    expect(await screen.findByText('students.read')).toBeInTheDocument()
    expect(screen.getByText('Inherited role grant · read-only')).toBeInTheDocument()

    const granted = screen.getByRole('checkbox', { name: /attendance.manage/ })
    await waitFor(() => expect(granted).toBeChecked())
    expect(granted).toBeDisabled()
    await startEditing()
    fireEvent.click(granted)
    expect(granted).not.toBeChecked()
    expect(screen.getByText('Will be revoked')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => {
      expect(api.changeStaffPermissions).toHaveBeenCalledWith('jwt', 'staff-1', ['attendance.manage'], 'revoke')
    })
    expect(api.changeStaffPermissions).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('Permissions updated successfully')).toBeInTheDocument()
  })

  it('grants ticked and revokes unticked permissions in one save', async () => {
    const after = {
      ...state,
      permissions: [
        state.permissions[0],
        { code: 'attendance.manage', inherited: false, direct_grant_id: null },
        { code: 'documents.read', inherited: false, direct_grant_id: 'grant-2' },
      ],
    }
    vi.mocked(api.changeStaffPermissions).mockResolvedValue({ changed: 1, permissions: after })
    render(<StaffPermissionManager accessToken="jwt" />)
    await waitFor(() => expect(screen.getByRole('checkbox', { name: /attendance.manage/ })).toBeChecked())
    await startEditing()
    fireEvent.click(screen.getByRole('checkbox', { name: /documents.read/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /attendance.manage/ }))
    expect(screen.getByText('1 to grant · 1 to revoke')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.changeStaffPermissions).toHaveBeenCalledTimes(2))
    expect(api.changeStaffPermissions).toHaveBeenCalledWith('jwt', 'staff-1', ['documents.read'], 'grant')
    expect(api.changeStaffPermissions).toHaveBeenCalledWith('jwt', 'staff-1', ['attendance.manage'], 'revoke')
    expect(await screen.findByText('Permissions updated successfully')).toBeInTheDocument()
    expect(screen.getByText('2 permission grant(s) changed.')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /documents.read/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /attendance.manage/ })).not.toBeChecked()
    // Saving returns the list to read-only.
    expect(screen.getByRole('button', { name: 'Edit permissions' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /documents.read/ })).toBeDisabled()
  })

  it('surfaces backend failures without reporting a successful mutation', async () => {
    vi.mocked(api.changeStaffPermissions).mockRejectedValue(new Error('Permission denied'))
    render(<StaffPermissionManager accessToken="jwt" />)
    await screen.findByText('students.read')
    await startEditing()
    fireEvent.click(screen.getByRole('checkbox', { name: /documents.read/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Permission denied')
    expect(screen.queryByText(/Permissions updated/)).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /documents.read/ })).toBeChecked()
  })

  it('lets a ticked permission be unticked again before saving', async () => {
    render(<StaffPermissionManager accessToken="jwt" />)
    await screen.findByText('students.read')
    await startEditing()
    const checkbox = screen.getByRole('checkbox', { name: /documents.read/ })
    const save = screen.getByRole('button', { name: 'Save changes' })
    for (let round = 0; round < 3; round += 1) {
      fireEvent.click(checkbox)
      expect(checkbox).toBeChecked()
      expect(save).toBeEnabled()
      fireEvent.click(checkbox)
      expect(checkbox).not.toBeChecked()
      expect(save).toBeDisabled()
    }
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(checkbox).not.toBeChecked()
    expect(checkbox).toBeDisabled()
    expect(api.changeStaffPermissions).not.toHaveBeenCalled()
  })

  it('does not offer inherited permissions as direct-grant controls', async () => {
    render(<StaffPermissionManager accessToken="jwt" />)
    await screen.findByText('students.read')
    expect(screen.queryByLabelText('students.read')).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /documents.read/ })).toBeInTheDocument()
  })
})

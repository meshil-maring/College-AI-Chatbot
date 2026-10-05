import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StaffPermissionManager from './StaffPermissionManager.tsx'
import * as api from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')

const state = {
  user_id: 'staff-1',
  institution_id: 'institution-1',
  permissions: [
    { code: 'students.read', inherited: true, direct_grant_id: null },
    { code: 'attendance.manage', inherited: false, direct_grant_id: 'grant-1' },
  ],
  delegable_permissions: ['attendance.manage', 'documents.read'],
}

describe('StaffPermissionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [{
        user_id: 'staff-1',
        email: 'staff@example.test',
        name: 'Staff One',
        role: 'staff',
        status: 'active',
      }],
      total: 1,
    })
    vi.mocked(api.getDelegableStaffPermissions).mockResolvedValue([
      'attendance.manage',
      'documents.read',
    ])
    vi.mocked(api.getStaffPermissions).mockResolvedValue(state)
  })

  it('shows inherited grants as read-only and permits revoking direct grants', async () => {
    vi.mocked(api.changeStaffPermissions).mockResolvedValue({ changed: 1, permissions: state })
    render(<StaffPermissionManager accessToken="jwt" />)
    expect(await screen.findByText('students.read')).toBeInTheDocument()
    expect(screen.getByText('Inherited role grant · read-only')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox', { name: /attendance.manage/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Revoke selected direct grants' }))
    await waitFor(() => {
      expect(api.changeStaffPermissions).toHaveBeenCalledWith(
        'jwt',
        'staff-1',
        ['attendance.manage'],
        'revoke',
      )
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Revoke completed.')
  })

  it('surfaces backend failures without reporting a successful mutation', async () => {
    vi.mocked(api.changeStaffPermissions).mockRejectedValue(new Error('Permission denied'))
    render(<StaffPermissionManager accessToken="jwt" />)
    await screen.findByText('students.read')
    fireEvent.click(screen.getByRole('checkbox', { name: /documents.read/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Grant selected' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Permission denied')
    expect(screen.queryByText(/Grant completed/)).not.toBeInTheDocument()
  })

  it('does not offer inherited permissions as direct-grant controls', async () => {
    render(<StaffPermissionManager accessToken="jwt" />)
    await screen.findByText('students.read')
    expect(screen.queryByLabelText('students.read')).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /documents.read/ })).toBeInTheDocument()
  })
})

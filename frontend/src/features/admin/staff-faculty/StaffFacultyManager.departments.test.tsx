import './__tests__/StaffFacultyManager.support.ts'
import { actionNames, chooseAction, CSE, MECH, member, request } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as academics from '../../../services/admin/academics.ts'
import * as api from '../../../services/admin/adminApi.ts'

describe('Staff and Faculty Management — departments', () => {
  it('requires the administrator to choose a department before approving', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    const select = await screen.findByRole('combobox', { name: 'Department for Ada Faculty' })
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeEnabled()
    // Only active departments are offered, sorted by name.
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Choose department…', 'Computer Science (CSE)', 'Mechanical (ME)'])
    fireEvent.change(select, { target: { value: MECH.department_id } })
    expect(screen.getByRole('button', { name: 'Approve' })).toBeEnabled()
  })

  it('explains that departments must exist before requests can be approved', async () => {
    vi.mocked(academics.getAcademicSetup).mockResolvedValue({
      institution_id: 'institution-1',
      records: { departments: [] },
      manageable: [],
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText(/No active departments yet/)).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Department for Ada Faculty' })).toBeDisabled()
  })

  it('still shows requests when departments cannot be loaded', async () => {
    vi.mocked(academics.getAcademicSetup).mockRejectedValue(new Error('down'))
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText(request.full_name)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Could not load departments')
  })

  it('shows each member department and lets the administrator change it', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [member({ department_id: CSE.department_id, department_code: 'CSE', department_name: CSE.name })],
      total: 1,
    })
    vi.mocked(api.setMemberDepartment).mockResolvedValue({
      user_id: member().user_id,
      department_id: MECH.department_id,
      department_code: 'ME',
      department_name: 'Mechanical',
      message: 'Department set to Mechanical.',
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const select = await screen.findByRole('combobox', { name: 'Department for Sam Staff' })
    expect(select).toHaveValue(CSE.department_id)
    fireEvent.change(select, { target: { value: MECH.department_id } })
    await waitFor(() =>
      expect(api.setMemberDepartment).toHaveBeenCalledWith('jwt', member().user_id, MECH.department_id),
    )
    expect(await screen.findByText('Department set to Mechanical.')).toBeInTheDocument()
  })

  it('does not change the department when the administrator cancels', async () => {
    vi.mocked(window.confirm).mockReturnValue(false)
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member()], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const select = await screen.findByRole('combobox', { name: 'Department for Sam Staff' })
    expect(select).toHaveValue('')
    fireEvent.change(select, { target: { value: CSE.department_id } })
    expect(api.setMemberDepartment).not.toHaveBeenCalled()
  })
})

describe('Staff and Faculty Management — permissions', () => {
  it('opens a Staff member permissions from the roster', async () => {
    const other = member({ user_id: '20000000-0000-0000-0000-000000000002', name: 'Pat Staff', email: 'pat@x.test' })
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member(), other], total: 2 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(screen.queryByRole('heading', { name: 'Staff permissions' })).toBeNull()
    await chooseAction('Pat Staff', 'Permissions')
    // Permissions opens the Staff permissions page with that member selected.
    expect(await screen.findByRole('heading', { name: 'Staff permissions' })).toBeInTheDocument()
    await waitFor(() => expect(api.getStaffPermissions).toHaveBeenLastCalledWith('jwt', other.user_id))
    expect(screen.getByRole('combobox', { name: 'Staff member' })).toHaveValue(other.user_id)
  })

  it('offers permissions only for active Staff, not Faculty', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [member({ role: 'faculty', name: 'Fay Faculty' }), member({ user_id: 's2', status: 'deactivated' })],
      total: 2,
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(await actionNames('Fay Faculty')).not.toContain('Permissions')
    expect(await actionNames('Sam Staff')).toEqual(['Reactivate'])
  })

  it('hides permission management from an administrator without that grant', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member()], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" canManagePermissions={false} />)
    expect(await actionNames('Sam Staff')).toEqual(['Deactivate'])
    expect(screen.queryByRole('heading', { name: 'Staff permissions' })).toBeNull()
    expect(api.getDelegableStaffPermissions).not.toHaveBeenCalled()
  })
})

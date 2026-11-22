import '../__tests__/StaffFacultyManager.support.ts'
import { CSE, member } from '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'

const teacher = member({
  user_id: 'f-1',
  name: 'Tina Teacher',
  role: 'faculty',
  department_id: CSE.department_id,
  department_name: CSE.name,
  employee_id: 'EMP-7',
  designation: 'Assistant Professor',
  employment_type: 'contractual',
  employment_status: 'contract_ended',
  additional_department_names: ['Mechanical'],
})
const clerk = member({ user_id: 's-1', name: 'Sam Staff', status: 'suspended' })

async function openDirectory() {
  vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher, clerk], total: 2 })
  vi.mocked(api.listInstitutionAdmins).mockResolvedValue({
    owner_user_id: 'a-1',
    viewer_is_owner: true,
    invitations: [],
    administrators: [
      {
        user_id: 'a-1',
        name: 'Olive Owner',
        email: 'olive@example.com',
        status: 'active',
        assigned_at: null,
        is_owner: true,
      },
    ],
  })
  vi.mocked(api.listMembershipInvitations).mockResolvedValue({
    total: 1,
    invitations: [
      {
        invitation_id: 'i-1',
        email: 'new@example.com',
        full_name: 'Nia New',
        role: 'staff',
        department_id: CSE.department_id,
        employee_id: 'STF-9',
        designation: 'Clerk',
        status: 'invited',
        expires_at: '2099-01-01T00:00:00Z',
        created_at: null,
        email_delivery_status: 'sent',
        resend_count: 0,
        last_sent_at: null,
      },
    ],
  })
  render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
  return screen.findByRole('region', { name: 'Staff and faculty roster' })
}

describe('User directory', () => {
  it('lists members, administrators and pending invitations together', async () => {
    const table = await openDirectory()
    expect(await within(table).findByText('Olive Owner')).toBeInTheDocument()
    expect(within(table).getByText('Owner')).toBeInTheDocument()
    expect(within(table).getByText('Nia New')).toBeInTheDocument()
    expect(within(table).getByText('Invitation pending')).toBeInTheDocument()
    expect(within(table).getByText('EMP-7')).toBeInTheDocument()
    expect(within(table).getByText('Contractual · contract ended')).toBeInTheDocument()
    expect(within(table).getByText('Also: Mechanical')).toBeInTheDocument()
    expect(screen.getByText('4 people')).toBeInTheDocument()
  })

  it('filters by user type, status, employment and searches employee IDs', async () => {
    const table = await openDirectory()
    await within(table).findByText('Olive Owner')
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by role' }), { target: { value: 'admin' } })
    expect(within(table).getByText('Olive Owner')).toBeInTheDocument()
    expect(within(table).queryByText('Tina Teacher')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by status' }), { target: { value: 'pending' } })
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by status' }), { target: { value: 'suspended' } })
    expect(within(table).getByText('Sam Staff')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by employment status' }), {
      target: { value: 'contract_ended' },
    })
    expect(within(table).getByText('Tina Teacher')).toBeInTheDocument()
    expect(within(table).queryByText('Sam Staff')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'stf-9' } })
    expect(within(table).getByText('Nia New')).toBeInTheDocument()
    expect(within(table).queryByText('Tina Teacher')).toBeNull()
  })

  it('sends administrators and invitations to the page that manages them', async () => {
    const table = await openDirectory()
    fireEvent.click(await within(table).findByRole('button', { name: 'Manage Olive Owner on Administrators' }))
    expect(await screen.findByRole('region', { name: 'Administrators' })).toBeInTheDocument()
  })

  it('suspends an active member and reactivates a suspended one', async () => {
    vi.mocked(api.changeMembershipStatus).mockResolvedValue({
      user_id: 'f-1',
      status: 'suspended',
      already_applied: false,
      message: 'Member suspended.',
    })
    await openDirectory()
    fireEvent.click(await screen.findByRole('button', { name: 'Actions for Tina Teacher' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Suspend' }))
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Suspend Tina Teacher?'))
    await waitFor(() => expect(api.changeMembershipStatus).toHaveBeenCalledWith('jwt', 'f-1', 'suspend'))
    expect(await screen.findByText('Member suspended.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Actions for Sam Staff' }))
    const items = within(screen.getByRole('menu'))
      .getAllByRole('menuitem')
      .map((item) => item.textContent)
    expect(items).toEqual(['Edit profile', 'History', 'Deactivate', 'Reactivate'])
  })
})

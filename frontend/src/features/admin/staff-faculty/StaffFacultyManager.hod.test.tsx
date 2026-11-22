import './__tests__/StaffFacultyManager.support.ts'
import { actionNames, chooseAction, CSE, MECH, member } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'
import * as transfers from '../../../services/students/transferApi.ts'

const teacher = member({ name: 'Tina Teacher', role: 'faculty', department_id: CSE.department_id })

function head(userId: string, name: string, departmentId = CSE.department_id) {
  return {
    department_id: departmentId,
    faculty_user_id: userId,
    name,
    email: null,
    assigned_at: '2026-11-21T00:00:00Z',
    starts_on: '2026-11-21',
    planned_end_on: null,
    is_active_faculty: true,
  }
}

function withHeads(heads: ReturnType<typeof head>[], allow = true) {
  vi.mocked(transfers.getDepartmentHeads).mockResolvedValue({
    institution_id: 'institution-1',
    allow_multi_department_hod: allow,
    heads,
    faculty: [],
  })
}

// New appointments start today (UTC) with no planned end unless changed.
const TODAY_TERM = { starts_on: new Date().toISOString().slice(0, 10), planned_end_on: null }

function change(departmentId: string) {
  return {
    department_id: departmentId,
    faculty_user_id: teacher.user_id,
    institution_id: 'institution-1',
    already_applied: false,
    head_ids: [teacher.user_id],
  }
}

async function openDialog() {
  await chooseAction('Tina Teacher', 'Manage HOD')
  return screen.getByRole('dialog', { name: 'Head of Department' })
}

describe('Staff and Faculty Management — Head of Department', () => {
  it('appoints one faculty member as HOD of several departments', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.addDepartmentHead).mockImplementation(async (_token, id) => change(id))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const dialog = await openDialog()
    expect(within(dialog).getByRole('button', { name: 'Save' })).toBeDisabled()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Computer Science/ }))
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(transfers.addDepartmentHead).toHaveBeenCalledTimes(2))
    expect(transfers.addDepartmentHead).toHaveBeenCalledWith('jwt', CSE.department_id, teacher.user_id, TODAY_TERM)
    expect(transfers.addDepartmentHead).toHaveBeenCalledWith('jwt', MECH.department_id, teacher.user_id, TODAY_TERM)
    expect(transfers.assignDepartmentHead).not.toHaveBeenCalled()
    expect(
      await screen.findByText('Tina Teacher is now Head of Department of Computer Science and Mechanical.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('adds a co-HOD without ending the current head', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    withHeads([head('someone-else', 'Old Head')])
    vi.mocked(transfers.addDepartmentHead).mockImplementation(async (_token, id) => change(id))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const dialog = await openDialog()
    const option = within(dialog).getByRole('checkbox', { name: /Computer Science/ })
    expect(option.closest('label')).toHaveTextContent('Also headed by Old Head')
    fireEvent.click(option)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(transfers.addDepartmentHead).toHaveBeenCalledWith('jwt', CSE.department_id, teacher.user_id, TODAY_TERM),
    )
    expect(transfers.endDepartmentHead).not.toHaveBeenCalled()
  })

  it('shows one badge per department and ends a single appointment', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    withHeads([head(teacher.user_id, 'Tina Teacher'), head(teacher.user_id, 'Tina Teacher', MECH.department_id)])
    vi.mocked(transfers.endDepartmentHead).mockImplementation(async (_token, id) => change(id))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(await screen.findByText('HOD · Computer Science')).toBeInTheDocument()
    expect(screen.getByText('HOD · Mechanical')).toBeInTheDocument()
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(transfers.endDepartmentHead).toHaveBeenCalledWith('jwt', MECH.department_id, teacher.user_id),
    )
    expect(transfers.endDepartmentHead).toHaveBeenCalledTimes(1)
    expect(transfers.addDepartmentHead).not.toHaveBeenCalled()
    expect(await screen.findByText('Tina Teacher is now Head of Department of Computer Science.')).toBeInTheDocument()
  })

  it('removes every appointment and keeps the member as Faculty', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    withHeads([head(teacher.user_id, 'Tina Teacher', MECH.department_id)])
    vi.mocked(transfers.endDepartmentHead).mockImplementation(async (_token, id) => change(id))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    expect(await screen.findByText(/no longer a Head of Department\. They remain Faculty/)).toBeInTheDocument()
  })

  it('does not change anything when the dialog is cancelled', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(transfers.addDepartmentHead).not.toHaveBeenCalled()
  })

  it('never offers HOD to Staff or to inactive Faculty without an appointment', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [member({ department_id: CSE.department_id }), { ...teacher, user_id: 't2', status: 'deactivated' }],
      total: 2,
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(await actionNames('Sam Staff')).toEqual(['Edit profile', 'History', 'Permissions', 'Suspend', 'Deactivate'])
    expect(await actionNames('Tina Teacher')).toEqual(['Edit profile', 'History', 'Reactivate'])
  })

  it('reports partial progress when a later change is refused', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.addDepartmentHead)
      .mockImplementationOnce(async (_token, id) => change(id))
      .mockRejectedValueOnce(new Error('Choose an active faculty member for an active department.'))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Computer Science/ }))
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Saved 1 of 2 changes. Choose an active faculty member')
  })

  it('keeps the roster usable when HOD data cannot be loaded', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.getDepartmentHeads).mockRejectedValue(new Error('down'))
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(await screen.findByText('Tina Teacher')).toBeInTheDocument()
    expect(screen.queryByText(/HOD ·/)).toBeNull()
  })
})

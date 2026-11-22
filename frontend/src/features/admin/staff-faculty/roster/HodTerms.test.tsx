import '../__tests__/StaffFacultyManager.support.ts'
import { chooseAction, CSE, MECH, member } from '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'
import * as transfers from '../../../../services/students/transferApi.ts'

const teacher = member({ name: 'Tina Teacher', role: 'faculty', department_id: CSE.department_id })
const today = new Date().toISOString().slice(0, 10)
const inDays = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10)

function headsOf(departments: string[], allow = true) {
  vi.mocked(transfers.getDepartmentHeads).mockResolvedValue({
    institution_id: 'institution-1',
    allow_multi_department_hod: allow,
    faculty: [],
    heads: departments.map((department_id) => ({
      department_id,
      faculty_user_id: teacher.user_id,
      name: 'Tina Teacher',
      email: null,
      assigned_at: '2026-11-01T00:00:00Z',
      starts_on: '2026-11-01',
      planned_end_on: null,
      is_active_faculty: true,
    })),
  })
}

async function openDialog() {
  vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
  render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
  await chooseAction('Tina Teacher', 'Manage HOD')
  return screen.getByRole('dialog', { name: 'Head of Department' })
}

describe('Head of Department terms', () => {
  it('saves a changed planned end date without re-appointing', async () => {
    headsOf([CSE.department_id])
    vi.mocked(transfers.setDepartmentHeadTerm).mockResolvedValue({})
    const dialog = await openDialog()
    expect(within(dialog).getByLabelText('Starts on')).toHaveValue('2026-11-01')
    fireEvent.change(within(dialog).getByLabelText('Planned end (optional)'), { target: { value: inDays(30) } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(transfers.setDepartmentHeadTerm).toHaveBeenCalledWith('jwt', CSE.department_id, teacher.user_id, {
        starts_on: '2026-11-01',
        planned_end_on: inDays(30),
      }),
    )
    expect(transfers.addDepartmentHead).not.toHaveBeenCalled()
    expect(transfers.endDepartmentHead).not.toHaveBeenCalled()
  })

  it('explains invalid dates and keeps Save disabled', async () => {
    headsOf([])
    const dialog = await openDialog()
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    expect(within(dialog).getByLabelText('Starts on')).toHaveValue(today)
    fireEvent.change(within(dialog).getByLabelText('Starts on'), { target: { value: inDays(2) } })
    expect(within(dialog).getByText('The start date cannot be in the future.')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Save' })).toBeDisabled()
    fireEvent.change(within(dialog).getByLabelText('Starts on'), { target: { value: today } })
    fireEvent.change(within(dialog).getByLabelText('Planned end (optional)'), { target: { value: inDays(-3) } })
    expect(within(dialog).getByText('The planned end cannot be before the start.')).toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Planned end (optional)'), { target: { value: inDays(90) } })
    expect(within(dialog).getByRole('button', { name: 'Save' })).toBeEnabled()
  })

  it('allows only one department when the institution policy says so', async () => {
    headsOf([MECH.department_id], false)
    const dialog = await openDialog()
    expect(within(dialog).getByText(/allows one department per Head of Department/)).toBeInTheDocument()
    expect(within(dialog).getByRole('checkbox', { name: /Computer Science/ })).toBeDisabled()
    // Moving to another department: end the current one, then the others unlock.
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /Mechanical/ }))
    expect(within(dialog).getByRole('checkbox', { name: /Computer Science/ })).toBeEnabled()
  })
})

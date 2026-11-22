import '../__tests__/StaffFacultyManager.support.ts'
import { CSE, MECH, chooseAction, member } from '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'

const teacher = member({ user_id: 'f-1', name: 'Tina Teacher', role: 'faculty', department_id: CSE.department_id })

async function openProfile() {
  vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
  vi.mocked(api.getMemberProfile).mockResolvedValue({
    user_id: 'f-1',
    role: 'faculty',
    employment_status: 'active',
    common: { employee_id: 'EMP-7', phone: null, designation: 'Lecturer', joining_date: '2026-06-01' },
    faculty: {
      employment_type: 'permanent',
      employment_start_date: '2026-06-01',
      qualification: 'M.Tech',
      experience_years: 4,
    },
    staff: null,
    primary_department: { department_id: CSE.department_id, code: 'CSE', name: CSE.name },
    additional_departments: [],
  })
  render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
  await chooseAction('Tina Teacher', 'Edit profile')
  const dialog = screen.getByRole('dialog', { name: 'Edit profile' })
  await within(dialog).findByDisplayValue('EMP-7')
  return dialog
}

describe('Edit profile', () => {
  it('starts from the saved profile and saves only what changed', async () => {
    vi.mocked(api.saveMemberProfile).mockResolvedValue({ user_id: 'f-1', role: 'faculty', message: 'saved' })
    vi.mocked(api.setMemberAdditionalDepartments).mockResolvedValue({
      user_id: 'f-1',
      additional_departments: [],
      message: 'saved',
    })
    const dialog = await openProfile()
    expect(within(dialog).getByLabelText(/Qualification/)).toHaveValue('M.Tech')
    expect(within(dialog).getByLabelText(/Experience/)).toHaveValue(4)
    fireEvent.change(within(dialog).getByLabelText(/Designation/), { target: { value: 'Assistant Professor' } })
    fireEvent.click(within(dialog).getByRole('checkbox', { name: MECH.name }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save profile' }))
    await waitFor(() =>
      expect(api.saveMemberProfile).toHaveBeenCalledWith('jwt', 'f-1', {
        common: { employee_id: 'EMP-7', phone: null, designation: 'Assistant Professor', joining_date: '2026-06-01' },
        faculty: {
          employment_type: 'permanent',
          employment_start_date: '2026-06-01',
          contract_end_date: null,
          qualification: 'M.Tech',
          specialization: null,
          experience_years: 4,
        },
      }),
    )
    expect(api.setMemberAdditionalDepartments).toHaveBeenCalledWith('jwt', 'f-1', [MECH.department_id])
    expect(api.setMemberDepartment).not.toHaveBeenCalled()
    expect(await screen.findByText('Profile of Tina Teacher saved.')).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Edit profile' })).toBeNull()
  })

  it('checks fields like Add member and keeps the dialog open on a refusal', async () => {
    vi.mocked(api.saveMemberProfile).mockRejectedValue(
      new Error('This employee ID is already used in your institution.'),
    )
    const dialog = await openProfile()
    fireEvent.change(within(dialog).getByLabelText(/Employee ID/), { target: { value: 'EMP 7' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save profile' }))
    expect(within(dialog).getByText(/Use up to 40 letters/)).toBeInTheDocument()
    expect(api.saveMemberProfile).not.toHaveBeenCalled()
    fireEvent.change(within(dialog).getByLabelText(/Employee ID/), { target: { value: 'EMP-8' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save profile' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('already used')
  })
})

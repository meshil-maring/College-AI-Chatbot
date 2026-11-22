import '../__tests__/StaffFacultyManager.support.ts'
import { CSE, member } from '../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as academics from '../../../../services/admin/academics.ts'
import * as api from '../../../../services/admin/adminApi.ts'
import * as structure from '../../../../services/admin/academicStructure.ts'
import * as transfers from '../../../../services/students/transferApi.ts'
import type { MemberResponsibility } from '../../../../types/admin/responsibilities.ts'

const teacher = member({ user_id: 'f-1', name: 'Tina Teacher', role: 'faculty' })
const SECTION = { academic_section_id: 's-1', name: 'CSE Year 2 A', code: 'CSE-2A', is_active: true }
const COURSE = { ...CSE, course_id: 'c-1', name: 'Databases', code: 'CS201', credits: 4 }

function record(changes: Partial<MemberResponsibility> = {}): MemberResponsibility {
  return {
    responsibility_id: 'r-1',
    responsibility: 'class_in_charge',
    faculty_user_id: 'f-1',
    faculty_name: 'Tina Teacher',
    academic_section_id: 's-1',
    course_id: null,
    target_code: 'CSE-2A',
    target_name: 'CSE Year 2 A',
    starts_on: '2026-11-01',
    planned_end_on: null,
    ended_at: null,
    is_current: true,
    ...changes,
  }
}

async function openPage(records: MemberResponsibility[] = []) {
  vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
  vi.mocked(api.listMemberResponsibilities).mockResolvedValue({ responsibilities: records, total: records.length })
  vi.mocked(structure.getAcademicStructure).mockResolvedValue({
    institution_id: 'institution-1',
    records: { academic_sections: [SECTION as never] },
    manageable: [],
    activities: [],
  })
  vi.mocked(academics.getAcademicSetup).mockResolvedValue({
    institution_id: 'institution-1',
    records: { departments: [CSE], courses: [COURSE as never] },
    manageable: [],
  })
  render(<StaffFacultyManager accessToken="jwt" defaultPage="responsibilities" />)
  return screen.findByRole('form', { name: 'Assign a responsibility' })
}

describe('Staff and Faculty — Responsibilities', () => {
  it('assigns a Class In-Charge to a section', async () => {
    vi.mocked(api.assignMemberResponsibility).mockResolvedValue({
      responsibility_id: 'r-2',
      already_applied: false,
      message: 'Class In-Charge assigned.',
    })
    const form = await openPage()
    await waitFor(() => expect(within(form).getByRole('option', { name: 'Tina Teacher' })).toBeInTheDocument())
    fireEvent.change(within(form).getByLabelText('Faculty member'), { target: { value: 'f-1' } })
    await waitFor(() => expect(within(form).getByRole('option', { name: 'CSE Year 2 A (CSE-2A)' })).toBeInTheDocument())
    fireEvent.change(within(form).getByLabelText('Class section'), { target: { value: 's-1' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Assign' }))
    await waitFor(() =>
      expect(api.assignMemberResponsibility).toHaveBeenCalledWith('jwt', {
        faculty_user_id: 'f-1',
        responsibility: 'class_in_charge',
        target_id: 's-1',
        starts_on: new Date().toISOString().slice(0, 10),
        planned_end_on: null,
      }),
    )
    expect(await screen.findByText('Class In-Charge assigned.')).toBeInTheDocument()
  })

  it('offers catalogue courses for a Subject Coordinator', async () => {
    const form = await openPage()
    fireEvent.change(within(form).getByLabelText('Responsibility'), { target: { value: 'subject_coordinator' } })
    expect(await within(form).findByRole('option', { name: 'Databases (CS201)' })).toBeInTheDocument()
    expect(within(form).queryByLabelText('Class section')).toBeNull()
  })

  it('ends a current appointment and shows history on request', async () => {
    vi.mocked(api.endMemberResponsibility).mockResolvedValue({
      responsibility_id: 'r-1',
      already_applied: false,
      message: 'Class In-Charge ended. It stays in the history.',
    })
    await openPage([
      record(),
      record({
        responsibility_id: 'r-0',
        faculty_name: 'Old Teacher',
        is_current: false,
        ended_at: '2026-10-01T00:00:00Z',
      }),
    ])
    const list = screen.getByRole('region', { name: 'Current appointments' })
    expect(await within(list).findByText('Tina Teacher')).toBeInTheDocument()
    expect(within(list).queryByText('Old Teacher')).toBeNull()
    fireEvent.click(within(list).getByRole('button', { name: 'Show history (1)' }))
    expect(screen.getByText('Old Teacher')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'End Tina Teacher as Class In-Charge of CSE Year 2 A' }))
    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(api.endMemberResponsibility).toHaveBeenCalledWith('jwt', 'r-1'))
    expect(await screen.findByText('Class In-Charge ended. It stays in the history.')).toBeInTheDocument()
  })

  it('changes the one-department HOD rule and reports refusals', async () => {
    vi.mocked(transfers.setDepartmentHeadPolicy).mockResolvedValue({})
    await openPage()
    const rule = screen.getByRole('checkbox', { name: /head more than one department/ })
    await waitFor(() => expect(rule).toBeChecked())
    fireEvent.click(rule)
    await waitFor(() => expect(transfers.setDepartmentHeadPolicy).toHaveBeenCalledWith('jwt', false))
    expect(await screen.findByText(/limited to one department per Head/)).toBeInTheDocument()
    vi.mocked(transfers.setDepartmentHeadPolicy).mockRejectedValue(new Error('You do not have permission.'))
    fireEvent.click(rule)
    expect(await screen.findByText('You do not have permission.')).toBeInTheDocument()
  })
})

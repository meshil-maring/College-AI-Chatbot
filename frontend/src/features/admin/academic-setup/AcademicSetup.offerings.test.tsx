import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab, AcademicRecordHarness } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'

function select(name: string, value: string) {
  fireEvent.change(screen.getByLabelText(name), { target: { value } })
}

function subjectOptions() {
  return within(screen.getByLabelText('Course / subject *'))
}

describe('named curriculum offering eligibility', () => {
  it('creates a named-only offering without creating a legacy curriculum link', async () => {
    const data = fixture()
    data.records.program_courses = []
    data.records.course_offerings = []
    data.offering_eligibility = [{ program_id: 'p', course_id: 'c', semester_id: 's', source: 'named_curriculum' }]
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicRecordHarness accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    expect(screen.getByRole('button', { name: /^Add / })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: /^Add / }))
    expect(within(screen.getByLabelText('Program *')).getByRole('option', { name: /Science degree/ })).toHaveValue('p')
    select('Program *', 'p')
    select('Academic year *', 'y')
    select('Semester *', 's')
    expect(subjectOptions().getByRole('option', { name: /Mathematics/ })).toHaveValue('c')
    expect(subjectOptions().queryByRole('option', { name: /Physics/ })).not.toBeInTheDocument()
    select('Course / subject *', 'c')
    expect(screen.getByRole('button', { name: 'Save record' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledExactlyOnceWith(
        'jwt',
        'course_offerings',
        { program_id: 'p', academic_year_id: 'y', semester_id: 's', course_id: 'c', capacity: null, is_active: true },
        undefined,
      ),
    )
    expect(data.records.program_courses).toEqual([])
  })

  it('combines exact new-term named eligibility with an old-term legacy link without broadening either', async () => {
    const data = fixture()
    data.records.program_courses![0].semester_id = 's'
    data.records.semesters!.push({
      semester_id: 'new-term',
      academic_year_id: 'y',
      name: 'Semester 2',
      code: 'S2',
      is_active: true,
    })
    data.records.programs!.push({
      program_id: 'other-program',
      department_id: 'd',
      name: 'Other degree',
      code: 'OTHER',
      is_active: true,
    })
    data.offering_eligibility = [
      { program_id: 'p', course_id: 'not-linked', semester_id: 'new-term', source: 'named_curriculum' },
    ]
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicRecordHarness accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    fireEvent.click(screen.getByRole('button', { name: /^Add / }))
    select('Program *', 'p')
    select('Academic year *', 'y')
    select('Semester *', 'new-term')
    expect(subjectOptions().getByRole('option', { name: /Physics/ })).toHaveValue('not-linked')
    expect(subjectOptions().queryByRole('option', { name: /Mathematics/ })).not.toBeInTheDocument()
    select('Course / subject *', 'not-linked')
    select('Semester *', 's')
    expect(screen.getByLabelText('Course / subject *')).toHaveValue('')
    expect(subjectOptions().getByRole('option', { name: /Mathematics/ })).toHaveValue('c')
    expect(subjectOptions().queryByRole('option', { name: /Physics/ })).not.toBeInTheDocument()
    select('Semester *', 'new-term')
    select('Program *', 'other-program')
    expect(subjectOptions().queryByRole('option', { name: /Physics/ })).not.toBeInTheDocument()
    expect(screen.getByText(/No curriculum subjects match this program and semester/)).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('does not use named metadata with an inactive academic ancestor to bypass prerequisites', async () => {
    const data = fixture()
    data.records.program_courses = []
    data.records.semesters![0].is_active = false
    data.offering_eligibility = [{ program_id: 'p', course_id: 'c', semester_id: 's', source: 'named_curriculum' }]
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicRecordHarness accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    expect(screen.getByRole('button', { name: /^Add / })).toBeDisabled()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
})

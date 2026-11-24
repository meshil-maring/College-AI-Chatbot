import './__tests__/AcademicSetup.support.ts'
import { catalogue, program, year } from './__tests__/AcademicSetup.support.ts'
import { populateExportCatalogue, semester, course } from './__tests__/academicExportFixtures.ts'
import * as api from '../../../services/admin/academics.ts'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AcademicSetup from './AcademicSetup.tsx'

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } })
}
async function add(page: string, singular: string) {
  fireEvent.click(await screen.findByRole('button', { name: page, exact: true }))
  fireEvent.click(screen.getByRole('button', { name: `Add ${singular}` }))
}
function choose(label: string, value: string) {
  fireEvent.change(screen.getByRole('combobox', { name: label, exact: true }), { target: { value } })
}

describe('export-aligned setup workflow', () => {
  it('creates a dated semester and a course with optional credits and teaching hours', async () => {
    populateExportCatalogue()
    catalogue.records.semesters = []
    catalogue.records.courses = []
    render(<AcademicSetup />)
    await add('Terms', 'term')
    fill('Name', semester.name)
    fill('Code', semester.code)
    choose('Academic year', year.academic_year_id)
    fill('Term number', '1')
    fill('Start date', semester.start_date)
    fill('End date', semester.end_date)
    expect(screen.queryByRole('combobox', { name: 'Degree program' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: semester.name })
    expect(api.createAcademicRecord).toHaveBeenLastCalledWith(
      'token-1',
      'semesters',
      expect.objectContaining({
        semester_number: 1,
        start_date: semester.start_date,
        end_date: semester.end_date,
        academic_year_id: year.academic_year_id,
      }),
    )
    await add('Courses', 'course')
    fill('Name', course.name)
    fill('Code', course.code)
    choose('Department', course.department_id)
    fill('Lecture hours (optional)', '3')
    fill('Practical hours (optional)', '2')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: course.name })
    expect(api.createAcademicRecord).toHaveBeenLastCalledWith(
      'token-1',
      'courses',
      expect.objectContaining({ credits: null, lecture_hours: 3, tutorial_hours: null, practical_hours: 2 }),
    )
  })
})

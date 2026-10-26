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
    await add('Semesters', 'semester')
    fill('Name', semester.name)
    fill('Code', semester.code)
    choose('Academic year', year.academic_year_id)
    fill('Semester number', '1')
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

  it('links a course, creates its offering, then creates a section for that offering', async () => {
    populateExportCatalogue()
    catalogue.records.program_courses = []
    catalogue.records.course_offerings = []
    catalogue.records.sections = []
    render(<AcademicSetup />)
    await add('Program courses', 'program course')
    expect(screen.queryByLabelText('Name', { exact: true })).not.toBeInTheDocument()
    choose('Degree program', program.program_id)
    choose('Course', course.course_id)
    choose('Course type', 'core')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    await screen.findByText('Saved successfully.')
    expect(api.createAcademicRecord).toHaveBeenLastCalledWith('token-1', 'program_courses', {
      program_id: program.program_id,
      course_id: course.course_id,
      semester_id: null,
      course_type: 'core',
      is_required: true,
      is_active: true,
    })
    await add('Course offerings', 'course offering')
    choose('Academic year', year.academic_year_id)
    choose('Degree program', program.program_id)
    choose('Course', course.course_id)
    choose('Semester', semester.semester_id)
    fill('Capacity (optional)', '60')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Saved successfully.')
    expect(api.createAcademicRecord).toHaveBeenLastCalledWith(
      'token-1',
      'course_offerings',
      expect.objectContaining({
        program_id: program.program_id,
        course_id: course.course_id,
        academic_year_id: year.academic_year_id,
        semester_id: semester.semester_id,
        capacity: 60,
      }),
    )
    await add('Sections', 'section')
    fill('Name', 'Section B')
    fill('Code', 'B')
    choose('Course offering', 'new-course_offerings')
    fill('Capacity (optional)', '30')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: 'Section B' })
    expect(api.createAcademicRecord).toHaveBeenLastCalledWith('token-1', 'sections', {
      name: 'Section B',
      code: 'B',
      course_offering_id: 'new-course_offerings',
      capacity: 30,
      is_active: true,
    })
    expect(screen.queryByRole('button', { name: /Manage subjects/ })).not.toBeInTheDocument()
  })
})

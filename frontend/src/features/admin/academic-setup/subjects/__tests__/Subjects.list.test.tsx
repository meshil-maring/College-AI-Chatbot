import { api, catalogue, department, subject, semester, link, renderSubjects } from './Subjects.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Subjects management list', () => {
  it('uses institution-scoped totals, subjects, departments and assignments', async () => {
    catalogue.records.courses!.push({
      ...subject,
      course_id: 'foreign',
      name: 'Foreign Subject',
      institution_id: 'foreign',
    })
    catalogue.records.departments!.push({
      ...department,
      department_id: 'foreign',
      name: 'Foreign Department',
      institution_id: 'foreign',
    })
    catalogue.records.program_courses!.push({ ...link, institution_id: 'foreign', course_type: 'project' })
    catalogue.records.semesters!.push({ ...semester, institution_id: 'foreign', name: 'Foreign Semester' })
    renderSubjects()
    await waitFor(
      () => expect(screen.getByRole('region', { name: 'Subject summary' })).toHaveAttribute('aria-busy', 'false'),
      { timeout: 5000 },
    )
    const row = screen.getByRole('row', { name: /Data Mining/ })
    expect(row).toHaveTextContent('Core')
    expect(row).not.toHaveTextContent('Project')
    const summary = within(screen.getByRole('region', { name: 'Subject summary' }))
    expect(summary.getByText('Total Subjects').parentElement).toHaveTextContent('1')
    expect(summary.getByText('Departments').parentElement).toHaveTextContent('1')
    expect(screen.queryByText('Foreign Subject')).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Foreign Department' })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Foreign Semester/ })).not.toBeInTheDocument()
  })

  it('paginates ten records, sorts codes and resets the page when searching', async () => {
    catalogue.records.courses = Array.from({ length: 12 }, (_, index) => ({
      ...subject,
      course_id: `s-${index}`,
      name: `Subject ${index + 1}`,
      code: `CS${index + 1}`,
    }))
    renderSubjects()
    await screen.findByText('Showing 1 to 10 of 12 subjects')
    expect(within(screen.getByRole('region', { name: 'Subject records' })).getAllByRole('row')[1]).toHaveTextContent(
      'CS1',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Next subject page' }))
    expect(screen.getByText('Showing 11 to 12 of 12 subjects')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search subjects' }), { target: { value: 'CS12' } })
    expect(screen.getByText('Showing 1 to 1 of 1 subjects')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous subject page' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Clear subject search' }))
    fireEvent.click(screen.getByRole('button', { name: 'Subject Code', exact: true }))
    expect(within(screen.getByRole('region', { name: 'Subject records' })).getAllByRole('row')[1]).toHaveTextContent(
      'CS12',
    )
  })

  it('combines filters against the same curriculum assignment', async () => {
    catalogue.records.semesters!.push({ ...semester, semester_id: 'semester-2', name: 'Spring', semester_number: 2 })
    catalogue.records.program_courses!.push({
      ...link,
      program_course_id: 'link-2',
      semester_id: 'semester-2',
      course_type: 'elective',
    })
    renderSubjects()
    await screen.findByRole('row', { name: /Data Mining/ })
    const filters = within(screen.getByRole('search', { name: 'Filter subjects' }))
    fireEvent.change(filters.getByRole('combobox', { name: 'Semester' }), { target: { value: 'semester-1' } })
    fireEvent.change(filters.getByRole('combobox', { name: 'Subject Type' }), { target: { value: 'elective' } })
    expect(screen.getByRole('heading', { name: 'No subjects match your filters' })).toBeInTheDocument()
    fireEvent.change(filters.getByRole('combobox', { name: 'Subject Type' }), { target: { value: 'core' } })
    expect(screen.getByRole('row', { name: /Data Mining/ })).toBeInTheDocument()
    fireEvent.change(filters.getByRole('combobox', { name: 'Status' }), { target: { value: 'inactive' } })
    expect(screen.getByRole('heading', { name: 'No subjects match your filters' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('Showing 1 to 1 of 1 subjects')).toBeInTheDocument()
  })

  it('distinguishes missing assignments from confirmed unassigned subjects', async () => {
    delete catalogue.records.program_courses
    renderSubjects()
    const row = await screen.findByRole('row', { name: /Data Mining/ })
    expect(within(row).getAllByText('Unavailable')).toHaveLength(2)
    expect(screen.getByRole('combobox', { name: 'Subject Type' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Semester' })).toBeDisabled()
  })

  it('opens the dedicated drawer from the overview shortcut without submitting', async () => {
    renderSubjects('overview')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Add Subject', exact: true }))
    expect(await screen.findByRole('dialog', { name: 'Add Subject' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Subjects', level: 1 })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })
})

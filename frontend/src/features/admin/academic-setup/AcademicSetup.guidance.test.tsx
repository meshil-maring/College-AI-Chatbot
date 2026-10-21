import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import type { AcademicCatalogue } from '../../../types/academicSetup.ts'
import AcademicSetup, { usable } from './AcademicSetup.tsx'
describe('AcademicSetup', () => {
  it('guides an empty college through numbered steps and points to missing prerequisites', async () => {
    const data = fixture()
    Object.keys(data.records).forEach((key) => {
      data.records[key as keyof typeof data.records] = []
    })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(screen.getByText('Suggested next step: 1. Departments')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
    const steps = within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getAllByRole('button')
    expect(steps.map((step) => step.getAttribute('aria-label'))).toEqual([
      'Departments, Step 1, 0 active records',
      'Programs, Step 2, 0 active records',
      'Academic Years, Step 3, 0 active records',
      'Semesters, Step 4, 0 active records',
      'Courses / Subjects, Step 5, 0 active records',
      'Program Curriculum, Step 6, 0 active records',
      'Course Offerings, Step 7, 0 active records',
      'Sections, Step 8, 0 active records',
      'Batches, Step 9, 0 active records',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Next: Programs' }))
    expect(screen.getByText('Step 2 of 9')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Step 1: Departments' }))
    expect(screen.getByText('Step 1 of 9')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('updates the suggested next step after saving and refreshing records', async () => {
    const empty = fixture()
    Object.keys(empty.records).forEach((key) => {
      empty.records[key as keyof typeof empty.records] = []
    })
    const saved = { ...empty, records: { ...empty.records, departments: fixture().records.departments } }
    vi.mocked(api.getAcademicCatalogue).mockResolvedValueOnce(empty).mockResolvedValue(saved)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Science' } })
    fireEvent.change(screen.getByLabelText('Code *'), { target: { value: 'SCI' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(await screen.findByText('Suggested next step: 2. Programs')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1')
    fireEvent.click(screen.getByRole('button', { name: 'Next: Programs' }))
    expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled()
  })

  it('counts usable records and keeps editing available when a prerequisite is inactive', async () => {
    const data = fixture()
    data.records.departments![0].is_active = false
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Programs')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2')
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit BS' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Edit BS' }))
    expect(screen.getByLabelText('Department *')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save record' })).toBeEnabled()
  })

  it('shows field examples and supports hover, keyboard dismissal and tapping without submitting', async () => {
    const user = userEvent.setup()
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(screen.getByLabelText('Name *')).toHaveAttribute('placeholder', 'e.g. Computer Science')
    expect(screen.getByLabelText('Name *')).toHaveAccessibleDescription(
      'Enter the official name, for example Computer Science.',
    )
    const help = screen.getByRole('button', { name: 'Help for Name' })
    fireEvent.mouseEnter(help)
    expect(screen.getByRole('tooltip')).toHaveTextContent('Enter the official name, for example Computer Science.')
    expect(help).toHaveAttribute('aria-describedby', screen.getByRole('tooltip').id)
    fireEvent.mouseLeave(help)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    fireEvent.focus(help)
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    fireEvent.keyDown(help, { key: 'Escape' })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    fireEvent.blur(help)
    await user.click(help)
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    await user.click(help)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('requires curriculum before offerings while allowing curriculum without an optional semester', async () => {
    const data = fixture()
    data.records.program_courses = []
    data.records.semesters = []
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Step 6: Program Curriculum' }))
    expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(
      within(screen.getByLabelText('Semester (optional)')).getByRole('option', { name: 'Any semester' }),
    ).toBeInTheDocument()
    fireEvent.mouseEnter(screen.getByRole('button', { name: 'Help for Semester (optional)' }))
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Selecting a semester limits this link to that exact term and academic year.',
    )
  })

  it('explains offering selection order and missing curriculum for the selected program', async () => {
    const data = fixture()
    data.records.programs!.push({
      program_id: 'p2',
      department_id: 'd',
      name: 'Other degree',
      code: 'OTHER',
      is_active: true,
    })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(screen.getByText('Choose an academic year first to see its semesters.')).toBeInTheDocument()
    expect(
      screen.getByText('Choose a program, academic year and semester first to see curriculum subjects.'),
    ).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Program *'), { target: { value: 'p2' } })
    fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('Semester *'), { target: { value: 's' } })
    expect(
      screen.getByText(
        'No curriculum subjects match this program and semester. Add a matching link in Step 6: Program Curriculum.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Course / subject *')).toHaveAccessibleDescription(
      expect.stringContaining('No curriculum subjects match'),
    )
  })

  it('limits progress and navigation to permitted steps and explains hidden dependencies', async () => {
    const data: AcademicCatalogue = { institution_id: 'tenant', manageable: ['courses'], records: { courses: [] } }
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    await screen.findByText('Step 5 of 9')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuemax', '1')
    expect(
      within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getAllByRole('button'),
    ).toHaveLength(1)
    expect(
      screen.getByText('Step 1: Departments — ask an administrator with access to this step for help.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open Step 1: Departments' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
  })

  it('keeps an unsaved form when navigating and allows continuing after cancel', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved department' } })
    expect(screen.getByRole('button', { name: 'Next: Programs' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Go to Sections' })).toBeDisabled()
    expect(
      within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getByRole('button', {
        name: /^Programs/,
      }),
    ).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next: Programs' }))
    expect(screen.getByText('Step 2 of 9')).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('does not treat a curriculum link to an inactive semester as ready for an offering', async () => {
    const data = fixture()
    data.records.program_courses![0].semester_id = 's'
    data.records.semesters![0].is_active = false
    expect(usable(data, 'program_courses', data.records.program_courses![0])).toBe(false)
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    expect(screen.getByRole('button', { name: 'Open Step 6: Program Curriculum' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
  })
})

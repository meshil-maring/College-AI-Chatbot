import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AcademicSetup, { usable } from './AcademicSetup.tsx'
import * as api from '../../services/adminApi.ts'
import type { AcademicCatalogue } from '../../types/academicSetup.ts'

vi.mock('../../services/adminApi.ts')
const fixture = (): AcademicCatalogue => ({
  institution_id: 'tenant', manageable: ['departments', 'programs', 'academic_years', 'semesters', 'courses', 'program_courses', 'course_offerings', 'sections'],
  records: {
    departments: [{ department_id: 'd', name: 'Science', code: 'SCI', is_active: true }, { department_id: 'inactive', name: 'Archived', code: 'OLD', is_active: false }],
    programs: [{ program_id: 'p', department_id: 'd', name: 'Science degree', code: 'BS', is_active: true }, { program_id: 'blocked', department_id: 'inactive', name: 'Unavailable', code: 'BAD', is_active: true }],
    academic_years: [{ academic_year_id: 'y', name: '2026-27', code: 'Y26', start_date: '2026-07-01', end_date: '2027-06-30', is_active: true }],
    semesters: [{ semester_id: 's', academic_year_id: 'y', name: 'Semester 1', code: 'S1', is_active: true }, { semester_id: 'other', academic_year_id: 'other-year', name: 'Foreign term', code: 'OTHER', is_active: true }],
    courses: [{ course_id: 'c', department_id: 'd', name: 'Mathematics', code: 'MATH', is_active: true }, { course_id: 'not-linked', department_id: 'd', name: 'Physics', code: 'PHY', is_active: true }],
    program_courses: [{ program_course_id: 'pc', program_id: 'p', course_id: 'c', semester_id: null, course_type: 'core', is_required: true, is_active: true }],
    course_offerings: [{ course_offering_id: 'o', program_id: 'p', course_id: 'c', academic_year_id: 'y', semester_id: 's', is_active: true }], sections: [],
  },
})
beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.getAcademicCatalogue).mockResolvedValue(fixture()); vi.mocked(api.saveAcademicRecord).mockResolvedValue({ saved: true }) })
async function loaded() { await screen.findByRole('button', { name: /^Add record$/ }) }
function tab(name: string) { fireEvent.click(within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getByRole('button', { name: new RegExp(`^${name}`) })) }

describe('AcademicSetup', () => {
  it('shows honest empty states and never creates data while loading', async () => {
    const data = fixture(); Object.keys(data.records).forEach((key) => { data.records[key as keyof typeof data.records] = [] })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded()
    expect(screen.getByText(/No departments have been entered/)).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
  it('creates a department without client actor or tenant fields', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Engineering' } }); fireEvent.change(screen.getByLabelText('Code *'), { target: { value: 'ENG' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() => expect(api.saveAcademicRecord).toHaveBeenCalledWith('jwt', 'departments', { name: 'Engineering', code: 'ENG', description: null, is_active: true }, undefined))
    expect(await screen.findByText('Academic record saved.')).toBeInTheDocument()
  })
  it('deactivates safely through an update and retains existing rows', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); fireEvent.click(screen.getByRole('button', { name: 'Edit SCI' }))
    fireEvent.click(screen.getByLabelText('Active')); fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() => expect(api.saveAcademicRecord).toHaveBeenCalledWith('jwt', 'departments', expect.objectContaining({ is_active: false }), 'd'))
    expect(screen.getByText('SCI · Science')).toBeInTheDocument()
  })
  it('offers only active departments when creating a program', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Programs'); fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    const options = within(screen.getByLabelText('Department *')).getAllByRole('option').map((option) => option.textContent)
    expect(options).toContain('SCI · Science'); expect(options).not.toContain('OLD · Archived')
  })
  it('cascades year/semester and program/curriculum subject selections', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Course Offerings'); fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(within(screen.getByLabelText('Program *')).queryByText('BAD · Unavailable')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Program *'), { target: { value: 'p' } }); fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: 'y' } })
    expect(within(screen.getByLabelText('Semester *')).queryByText('OTHER · Foreign term')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Semester *'), { target: { value: 's' } })
    expect(within(screen.getByLabelText('Course / subject *')).getByText('MATH · Mathematics')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Course / subject *')).queryByText('PHY · Physics')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Course / subject *'), { target: { value: 'c' } })
    fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: '' } })
    expect(screen.getByLabelText('Semester *')).toHaveValue(''); expect(screen.getByLabelText('Course / subject *')).toHaveValue('')
  })
  it('prevents a semester date range outside its academic year', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Semesters'); fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    for (const [name, value] of [['Academic year *', 'y'], ['Name *', 'Term'], ['Code *', 'T'], ['Semester number *', '2'], ['Start date *', '2025-07-01'], ['End date *', '2026-12-31']]) fireEvent.change(screen.getByLabelText(name), { target: { value } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Semester dates must fit'); expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
  it('keeps relationships fixed during edits and excludes them from patch payloads', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Course Offerings'); fireEvent.click(screen.getByRole('button', { name: 'Edit offering' }))
    expect(screen.getByLabelText('Program *')).toBeDisabled(); expect(screen.getByLabelText('Academic year *')).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Capacity'), { target: { value: '60' } }); fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() => expect(api.saveAcademicRecord).toHaveBeenCalledWith('jwt', 'course_offerings', { capacity: 60, is_active: true }, 'o'))
  })
  it('respects read-only permission projections', async () => {
    const data = fixture(); data.manageable = []; vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await screen.findByText('Read-only access')
    expect(screen.queryByRole('button', { name: 'Add record' })).not.toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Edit SCI' })).not.toBeInTheDocument()
  })
  it('surfaces duplicate errors without claiming success', async () => {
    vi.mocked(api.saveAcademicRecord).mockRejectedValue(new Error('Identifier already exists'))
    render(<AcademicSetup accessToken="jwt" />); await loaded(); fireEvent.click(screen.getByRole('button', { name: 'Edit SCI' })); fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Identifier already exists'); expect(screen.queryByText('Academic record saved.')).not.toBeInTheDocument()
  })
  it('retries unavailable reads without inventing records', async () => {
    vi.mocked(api.getAcademicCatalogue).mockRejectedValueOnce(new Error('Database unavailable'))
    render(<AcademicSetup accessToken="jwt" />); expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading' })); await loaded(); expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
  it('discards unsaved state when the session changes', async () => {
    const view = render(<AcademicSetup accessToken="old" />); await loaded(); fireEvent.click(screen.getByRole('button', { name: 'Add record' })); fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved old data' } })
    view.rerender(<AcademicSetup accessToken="new" />); await loaded(); expect(screen.queryByDisplayValue('Unsaved old data')).not.toBeInTheDocument()
    expect(api.getAcademicCatalogue).toHaveBeenCalledWith('new')
  })
  it('propagates inactive academic ancestors to section availability', () => {
    const data = fixture(), offering = data.records.course_offerings![0]
    expect(usable(data, 'course_offerings', offering)).toBe(true)
    data.records.departments![0].is_active = false
    expect(usable(data, 'course_offerings', offering)).toBe(false)
  })
  it('guides an empty college through numbered steps and points to missing prerequisites', async () => {
    const data = fixture(); Object.keys(data.records).forEach((key) => { data.records[key as keyof typeof data.records] = [] })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded()
    expect(screen.getByText('Suggested next step: 1. Departments')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
    const steps = within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getAllByRole('button')
    expect(steps.map((step) => step.getAttribute('aria-label'))).toEqual([
      'Departments, Step 1, 0 active records', 'Programs, Step 2, 0 active records',
      'Academic Years, Step 3, 0 active records', 'Semesters, Step 4, 0 active records',
      'Courses / Subjects, Step 5, 0 active records', 'Program Curriculum, Step 6, 0 active records',
      'Course Offerings, Step 7, 0 active records', 'Sections, Step 8, 0 active records',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Next: Programs' }))
    expect(screen.getByText('Step 2 of 8')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Step 1: Departments' }))
    expect(screen.getByText('Step 1 of 8')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
  it('updates the suggested next step after saving and refreshing records', async () => {
    const empty = fixture(); Object.keys(empty.records).forEach((key) => { empty.records[key as keyof typeof empty.records] = [] })
    const saved = { ...empty, records: { ...empty.records, departments: fixture().records.departments } }
    vi.mocked(api.getAcademicCatalogue).mockResolvedValueOnce(empty).mockResolvedValue(saved)
    render(<AcademicSetup accessToken="jwt" />); await loaded()
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
    const data = fixture(); data.records.departments![0].is_active = false
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Programs')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2')
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit BS' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Edit BS' }))
    expect(screen.getByLabelText('Department *')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save record' })).toBeEnabled()
  })
  it('shows field examples and supports hover, keyboard dismissal and tapping without submitting', async () => {
    const user = userEvent.setup()
    render(<AcademicSetup accessToken="jwt" />); await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(screen.getByLabelText('Name *')).toHaveAttribute('placeholder', 'e.g. Computer Science')
    expect(screen.getByLabelText('Name *')).toHaveAccessibleDescription('Enter the official name, for example Computer Science.')
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
    const data = fixture(); data.records.program_courses = []; data.records.semesters = []
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Course Offerings')
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Step 6: Program Curriculum' }))
    expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(within(screen.getByLabelText('Semester (optional)')).getByRole('option', { name: 'Any semester' })).toBeInTheDocument()
    fireEvent.mouseEnter(screen.getByRole('button', { name: 'Help for Semester (optional)' }))
    expect(screen.getByRole('tooltip')).toHaveTextContent('Selecting a semester limits this link to that exact term and academic year.')
  })
  it('explains offering selection order and missing curriculum for the selected program', async () => {
    const data = fixture(); data.records.programs!.push({ program_id: 'p2', department_id: 'd', name: 'Other degree', code: 'OTHER', is_active: true })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Course Offerings')
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(screen.getByText('Choose an academic year first to see its semesters.')).toBeInTheDocument()
    expect(screen.getByText('Choose a program, academic year and semester first to see curriculum subjects.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Program *'), { target: { value: 'p2' } })
    fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('Semester *'), { target: { value: 's' } })
    expect(screen.getByText('No curriculum subjects match this program and semester. Add a matching link in Step 6: Program Curriculum.')).toBeInTheDocument()
    expect(screen.getByLabelText('Course / subject *')).toHaveAccessibleDescription(expect.stringContaining('No curriculum subjects match'))
  })
  it('limits progress and navigation to permitted steps and explains hidden dependencies', async () => {
    const data: AcademicCatalogue = { institution_id: 'tenant', manageable: ['courses'], records: { courses: [] } }
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded()
    await screen.findByText('Step 5 of 8')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuemax', '1')
    expect(within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getAllByRole('button')).toHaveLength(1)
    expect(screen.getByText('Step 1: Departments — ask an administrator with access to this step for help.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open Step 1: Departments' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
  })
  it('keeps an unsaved form when navigating and allows continuing after cancel', async () => {
    render(<AcademicSetup accessToken="jwt" />); await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved department' } })
    expect(screen.getByRole('button', { name: 'Next: Programs' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Go to Sections' })).toBeDisabled()
    expect(within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getByRole('button', { name: /^Programs/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next: Programs' }))
    expect(screen.getByText('Step 2 of 8')).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })
  it('does not treat a curriculum link to an inactive semester as ready for an offering', async () => {
    const data = fixture(); data.records.program_courses![0].semester_id = 's'; data.records.semesters![0].is_active = false
    expect(usable(data, 'program_courses', data.records.program_courses![0])).toBe(false)
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />); await loaded(); tab('Course Offerings')
    expect(screen.getByRole('button', { name: 'Open Step 6: Program Curriculum' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add record' })).toBeDisabled()
  })
})

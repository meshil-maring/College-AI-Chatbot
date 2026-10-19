import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyStudents from './FacultyStudents.tsx'
import { queryClient } from '../../lib/queryClient.ts'
import {
  addFacultyAttendanceStudent,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceProfile,
  getFacultyAttendanceStudents,
  getFacultyStudentRegistrationHistory,
  type FacultyAttendanceRosterRow,
} from '../../services/facultyAttendanceApi.ts'

vi.mock('../../services/facultyAttendanceApi.ts', () => ({
  addFacultyAttendanceStudent: vi.fn(),
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceProfile: vi.fn(),
  getFacultyAttendanceStudents: vi.fn(),
  getFacultyStudentRegistrationHistory: vi.fn(),
}))

const assignment = {
  can_manage: true,
  assignment_id: 'section-1', assigned_at: '', section_id: 'section-1', semester_id: 'semester-1', academic_year_id: 'year-1',
  section: { section_id: 'section-1', name: 'Section A', code: 'A', course: { name: 'Data Mining', code: 'CS501' } },
}
const student: FacultyAttendanceRosterRow = {
  roster_id: 'roster-1', student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: 'UNI001',
  email: 'ada@college.edu', roster_status: 'ACTIVE', linked_student_id: 'student-1', attendance_percentage: 80,
}

beforeEach(() => {
  window.history.replaceState(null, '', '/faculty/students')
  vi.resetAllMocks()
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 1 })
  vi.mocked(getFacultyAttendanceProfile).mockResolvedValue({ student, section: assignment.section, total: 1,
    history: [{ record_id: 'record-1', session_date: '2026-10-15', status: 'present' }] })
  vi.mocked(getFacultyStudentRegistrationHistory).mockResolvedValue({ items: [], total: 0 })
})

describe('FacultyStudents', () => {
  it('navigates to a dedicated registration page and returns to the selected roster', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/register?section_id=section-1')
    expect(screen.getByRole('heading', { name: 'Register new student', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Section and subject' })).toHaveValue('section-1')
    expect(screen.queryByRole('region', { name: 'Student directory' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Back to students' })).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveFocus()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Unsaved draft')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/roster?section_id=section-1')
    expect(screen.getByRole('heading', { name: 'Students', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Section and subject' })).toHaveValue('section-1')
    expect(screen.getByRole('textbox', { name: 'Search students' })).toHaveValue('Ada')
    expect(screen.queryByRole('form', { name: 'Register student' })).not.toBeInTheDocument()
    expect(addFacultyAttendanceStudent).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
  })

  it('restores the list and registration page with browser Back and Forward', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await act(async () => { window.history.back() })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Students', level: 1 })).toBeInTheDocument())
    expect(window.location.pathname).toBe('/faculty/students')
    await act(async () => { window.history.forward() })
    expect(await screen.findByRole('heading', { name: 'Register new student', level: 1 })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students/register')
    expect(screen.getByRole('combobox', { name: 'Section and subject' })).toHaveValue('section-1')
  })

  it('opens and remounts a registration deep link for the requested authorized section', async () => {
    const second = { ...assignment, section_id: 'section-2', section: { ...assignment.section, section_id: 'section-2', name: 'Section B', code: 'B' } }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second])
    vi.mocked(addFacultyAttendanceStudent).mockResolvedValue(student)
    window.history.replaceState(null, '', '/faculty/students/register?section_id=section-2')
    const first = render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByRole('combobox', { name: 'Section and subject' })).toHaveValue('section-2')
    first.unmount()
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByRole('combobox', { name: 'Section and subject' })).toHaveValue('section-2')
    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await screen.findByRole('heading', { name: 'Students', level: 1 })
    expect(addFacultyAttendanceStudent).toHaveBeenCalledExactlyOnceWith('token', 'section-2', { student_name: 'Beena Shah', register_number: 'CS002' })
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/roster?section_id=section-2')
  })

  it.each(['unknown-section', 'read-only-section'])('denies registration deep links for %s without falling back to another section', async (sectionId) => {
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, { ...assignment, section_id: 'read-only-section', can_manage: false }])
    window.history.replaceState(null, '', `/faculty/students/register?section_id=${sectionId}`)
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByRole('heading', { name: 'Registration unavailable' })).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Register student' })).not.toBeInTheDocument()
    expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
    expect(addFacultyAttendanceStudent).not.toHaveBeenCalled()
  })

  it('registers a student in the selected section and refreshes an empty roster', async () => {
    const added: FacultyAttendanceRosterRow = { ...student, roster_id: 'new-roster', student_name: 'Beena Shah', register_number: 'CS002', university_roll_number: 'UNI002', email: 'beena@college.edu', roster_status: 'UNREGISTERED', linked_student_id: null, attendance_percentage: null }
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(addFacultyAttendanceStudent).mockImplementation(async () => {
      vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [added], total: 1 })
      return added
    })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('No students in this section yet')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    const form = screen.getByRole('form', { name: 'Register student' })
    await user.type(within(form).getByRole('textbox', { name: 'Student name (required)' }), ' Beena Shah ')
    await user.type(within(form).getByRole('textbox', { name: 'Register number (required)' }), ' CS002 ')
    await user.type(within(form).getByRole('textbox', { name: 'University roll number' }), ' UNI002 ')
    await user.type(within(form).getByRole('textbox', { name: 'Email (optional)' }), 'beena@college.edu')
    await user.click(within(form).getByRole('button', { name: 'Register student' }))
    expect(addFacultyAttendanceStudent).toHaveBeenCalledExactlyOnceWith('token', 'section-1', {
      student_name: 'Beena Shah', register_number: 'CS002', university_roll_number: 'UNI002', email: 'beena@college.edu',
    })
    expect(await screen.findByText('Beena Shah')).toBeInTheDocument()
    expect(screen.getByText('Beena Shah was added to Section A. Registration status: Unregistered.')).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
  })

  it('retains the form on duplicate errors and allows correction and retry', async () => {
    vi.mocked(addFacultyAttendanceStudent).mockRejectedValueOnce(new Error('Roster record already exists for this section'))
      .mockResolvedValueOnce({ ...student, student_name: 'Beena Shah', roster_status: 'UNREGISTERED' })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Roster record already exists')
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('Beena Shah')
    await user.clear(screen.getByRole('textbox', { name: 'Register number (required)' }))
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
    expect(addFacultyAttendanceStudent).toHaveBeenLastCalledWith('token', 'section-1', { student_name: 'Beena Shah', register_number: 'CS002' })
  })

  it('blocks blank names and register numbers and discards cancelled changes', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), '   ')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), '   ')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a student name and register number.')
    expect(addFacultyAttendanceStudent).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('prevents duplicate submission while a registration is pending', async () => {
    let finish!: (row: FacultyAttendanceRosterRow) => void
    vi.mocked(addFacultyAttendanceStudent).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.dblClick(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(screen.getByRole('button', { name: 'Registering student…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Section and subject' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Register number (required)' })).toBeDisabled()
    expect(addFacultyAttendanceStudent).toHaveBeenCalledTimes(1)
    await act(async () => finish(student))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
  })

  it('hides registration for read-only sections and closes the form when permissions are revoked', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([{ ...assignment, can_manage: false }])
    await act(async () => { await queryClient.invalidateQueries({ queryKey: ['faculty', 'students', 'token'] }) })
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Register new student' })).not.toBeInTheDocument())
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Registration unavailable' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Roster', exact: true }))
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
    expect(addFacultyAttendanceStudent).not.toHaveBeenCalled()
  })

  it('chooses an authorized section and subject on Register and saves to that section', async () => {
    const second = { ...assignment, section_id: 'section-2', section: { ...assignment.section, section_id: 'section-2', name: 'Section B', code: 'B', course: { name: 'Algorithms', code: 'CS502' } } }
    const readOnly = { ...assignment, can_manage: false, section_id: 'read-only-section', section: { ...assignment.section, section_id: 'read-only-section', name: 'Read only section' } }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second, readOnly])
    vi.mocked(addFacultyAttendanceStudent).mockResolvedValue(student)
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    const selector = screen.getByRole('combobox', { name: 'Section and subject' })
    expect(within(selector).getByRole('option', { name: /CS502.*Algorithms.*Section B/ })).toBeInTheDocument()
    expect(within(selector).queryByRole('option', { name: /Read only section/ })).not.toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Old draft')
    await user.selectOptions(selector, 'section-2')
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/register?section_id=section-2')
    expect(screen.getByRole('form', { name: 'Register student' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(addFacultyAttendanceStudent).toHaveBeenCalledExactlyOnceWith('token', 'section-2', { student_name: 'Beena Shah', register_number: 'CS002' }))
  })

  it('resets filters and pagination after registration so the full roster is visible', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 26 })
    vi.mocked(addFacultyAttendanceStudent).mockResolvedValue(student)
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Registration status' }), 'ACTIVE')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
    expect(screen.getByRole('textbox', { name: 'Search students' })).toHaveValue('')
    expect(screen.getByRole('combobox', { name: 'Registration status' })).toHaveValue('')
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('0'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe('')
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].has('registration')).toBe(false)
  })

  it('loads the authorized roster and retrieves details only when requested', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
    expect(screen.getByText('UNI001')).toBeInTheDocument()
    expect(screen.getByText('80.00%')).toBeInTheDocument()
    expect(getFacultyAttendanceProfile).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'View Ada Rao' }))
    const details = await screen.findByRole('region', { name: 'Student details' })
    expect(await within(details).findByText('2026-10-15')).toBeInTheDocument()
    expect(within(details).getByText('ada@college.edu')).toBeInTheDocument()
    expect(getFacultyAttendanceProfile).toHaveBeenCalledWith('token', 'roster-1', 0)
    await user.click(within(details).getByRole('button', { name: 'Close details' }))
    expect(screen.queryByRole('region', { name: 'Student details' })).not.toBeInTheDocument()
  })

  it('searches, filters and sorts on the server and resets pagination for new filters', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 26 })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenLastCalledWith('token', 'section-1', expect.any(URLSearchParams)))
    await screen.findByText('26–26 of 26 students')
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('25')
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'UNI001')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe('UNI001'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('0')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Registration status' }), 'PENDING_APPROVAL')
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL'))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sort by' }), 'student_name')
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('sort')).toBe('student_name'))
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].has('registration')).toBe(false))
    expect(screen.getByRole('textbox', { name: 'Search students' })).toHaveValue('')
  })

  it('shows real empty states for missing sections, empty rosters and unmatched searches', async () => {
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValueOnce([])
    const first = render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('No student rosters available')).toBeInTheDocument()
    expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
    first.unmount()
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [], total: 0 })
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('No students in this section yet')).toBeInTheDocument()
    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'missing')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    expect(await screen.findByText('No students match your filters')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
  })

  it('hides roster and profile data when a refreshed section read is denied, and supports retry', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'View Ada Rao' }))
    await screen.findByText('2026-10-15')
    vi.mocked(getFacultyAttendanceStudents).mockRejectedValueOnce(new Error('Section access denied'))
    await user.click(screen.getByRole('button', { name: 'Refresh students' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Section access denied')
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Student details' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
  })

  it('hides previously loaded students if section authorization can no longer be loaded', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    vi.mocked(getFacultyAttendanceAssignments).mockRejectedValueOnce(new Error('Access revoked'))
    await user.click(screen.getByRole('button', { name: 'Refresh sections' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Access revoked')
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
  })

  it('discards a late response when switching sections and resets search and details', async () => {
    const second = { ...assignment, section_id: 'section-2', assignment_id: 'section-2', section: { ...assignment.section, section_id: 'section-2', name: 'Section B', code: 'B' } }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second])
    let finish!: (result: { items: FacultyAttendanceRosterRow[]; total: number }) => void
    vi.mocked(getFacultyAttendanceStudents).mockImplementation((_token, section) => section === 'section-1'
      ? new Promise((resolve) => { finish = resolve })
      : Promise.resolve({ items: [{ ...student, roster_id: 'roster-2', student_name: 'Beena Shah' }], total: 1 }))
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByRole('combobox', { name: 'Section and subject' })
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'Ada')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Section and subject' }), 'section-2')
    expect(await screen.findByText('Beena Shah')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Search students' })).toHaveValue('')
    await act(async () => finish({ items: [student], total: 1 }))
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
  })

  it('clears student data when the identity or responsibility scope changes', async () => {
    const { rerender } = render(<FacultyStudents accessToken="token" scopeVersion="one" />)
    await screen.findByText('Ada Rao')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    rerender(<FacultyStudents accessToken="new-token" scopeVersion="two" />)
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
    expect(await screen.findByText('No student rosters available')).toBeInTheDocument()
    expect(getFacultyAttendanceAssignments).toHaveBeenLastCalledWith('new-token')
  })

  it('paginates student history and handles profile failures without rendering stale details', async () => {
    vi.mocked(getFacultyAttendanceProfile).mockResolvedValueOnce({ student, section: assignment.section, total: 51,
      history: [{ record_id: 'record-1', session_date: '2026-10-15', status: 'present' }] })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'View Ada Rao' }))
    await screen.findByText('2026-10-15')
    vi.mocked(getFacultyAttendanceProfile).mockRejectedValueOnce(new Error('Student access denied'))
    await user.click(screen.getByRole('button', { name: 'Next records' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Student access denied')
    expect(getFacultyAttendanceProfile).toHaveBeenLastCalledWith('token', 'roster-1', 50)
    expect(screen.queryByText('2026-10-15')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('2026-10-15')).toBeInTheDocument()
  })

  it('distinguishes absent attendance data from zero attendance', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [
      { ...student, attendance_percentage: null },
      { ...student, roster_id: 'roster-2', student_name: 'Beena Shah', attendance_percentage: 0, email: null, university_roll_number: null },
    ], total: 2 })
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('No records')).toBeInTheDocument()
    expect(screen.getByText('0.00%')).toBeInTheDocument()
    expect(screen.getByText('Email not recorded')).toBeInTheDocument()
  })
})

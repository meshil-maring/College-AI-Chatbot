import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyStudentsPage from './FacultyStudents.tsx'
import FacultyStudentsNavigation from './FacultyStudentsNavigation.tsx'
import { queryClient } from '../../lib/queryClient.ts'
import { addFacultyAttendanceStudent, getFacultyAttendanceAssignments, getFacultyAttendanceStudents, getFacultyStudentRegistrationHistory, type FacultyAttendanceRosterRow, type FacultyStudentRegistrationEvent } from '../../services/facultyAttendanceApi.ts'

vi.mock('../../services/facultyAttendanceApi.ts', () => ({
  getFacultyAttendanceAssignments: vi.fn(), getFacultyAttendanceStudents: vi.fn(), getFacultyStudentRegistrationHistory: vi.fn(),
  getFacultyAttendanceProfile: vi.fn(), addFacultyAttendanceStudent: vi.fn(),
}))
const assignment = { can_manage: true, assignment_id: 'section-1', section_id: 'section-1', assigned_at: '', semester_id: 'semester-1', academic_year_id: 'year-1', section: { section_id: 'section-1', name: 'Section A', code: 'A', course: { name: 'Data Mining', code: 'CS501' } } }
const pending = { roster_id: 'pending-1', student_name: 'Beena Shah', register_number: 'CS002', university_roll_number: null, email: 'beena@college.edu', roster_status: 'PENDING_APPROVAL' as const, linked_student_id: null }
const activity: FacultyStudentRegistrationEvent = { event_id: 'event-1', roster_id: 'roster-1', occurred_at: '2026-10-19T09:00:00Z', action: 'roster_added', student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: 'UNI001' }

function FacultyStudents({ accessToken }: { accessToken: string }) {
  return <>
    <aside><FacultyStudentsNavigation accessToken={accessToken} /></aside>
    <main><FacultyStudentsPage accessToken={accessToken} /></main>
  </>
}

beforeEach(() => {
  vi.resetAllMocks()
  window.history.replaceState(null, '', '/faculty/students/roster?section_id=section-1')
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceStudents).mockImplementation(async (_token, _section, query) => ({ items: query.get('registration') === 'PENDING_APPROVAL' ? [pending] : [{ ...pending, student_name: 'Roster student', roster_status: 'ACTIVE' }], total: 1 }))
  vi.mocked(getFacultyStudentRegistrationHistory).mockResolvedValue({ items: [activity], total: 1 })
})

describe('Students page navigation', () => {
  it('shows all four page links and preserves the section across their routes', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Roster student')
    const nav = screen.getByRole('navigation', { name: 'Students pages' })
    expect(nav.closest('aside')).not.toBeNull()
    expect(within(screen.getByRole('main')).queryByRole('navigation', { name: 'Students pages' })).not.toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Roster', exact: true })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Record history' })).toHaveAttribute('href', '/faculty/students/record-history?section_id=section-1')
    expect(within(nav).getByRole('link', { name: 'Waiting approval' })).toHaveAttribute('href', '/faculty/students/waiting-approval?section_id=section-1')
    expect(within(nav).getByRole('link', { name: 'Register', exact: true })).toHaveAttribute('href', '/faculty/students/register?section_id=section-1')
    await user.click(within(nav).getByRole('link', { name: 'Record history' }))
    expect(await screen.findByText('Added to roster')).toBeInTheDocument()
    expect(screen.queryByText('Roster student')).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Student directory' })).not.toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students/record-history')
    await user.click(within(nav).getByRole('link', { name: 'Waiting approval' }))
    expect(await screen.findByText('Beena Shah')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Student registration history' })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Registration status' })).not.toBeInTheDocument()
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL')
    await user.click(within(nav).getByRole('link', { name: 'Register', exact: true }))
    expect(screen.getByRole('heading', { name: 'Register new student', level: 1 })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Student directory' })).not.toBeInTheDocument()
    await user.click(within(nav).getByRole('link', { name: 'Roster', exact: true }))
    expect(await screen.findByText('Roster student')).toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/roster?section_id=section-1')
  })

  it('loads a history deep link, paginates and searches registration activity', async () => {
    window.history.replaceState(null, '', '/faculty/students/record-history?section_id=section-1')
    vi.mocked(getFacultyStudentRegistrationHistory).mockResolvedValue({ items: [activity], total: 26 })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Added to roster')
    expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Next history page' }))
    await waitFor(() => expect(vi.mocked(getFacultyStudentRegistrationHistory).mock.lastCall?.[2].get('offset')).toBe('25'))
    await user.type(screen.getByRole('textbox', { name: 'Search registration history' }), 'UNI001')
    await user.click(screen.getByRole('button', { name: 'Search history' }))
    await waitFor(() => expect(vi.mocked(getFacultyStudentRegistrationHistory).mock.lastCall?.[2].get('search')).toBe('UNI001'))
    expect(vi.mocked(getFacultyStudentRegistrationHistory).mock.lastCall?.[2].get('offset')).toBe('0')
  })

  it('keeps the current page when changing sections and discards a late history response', async () => {
    window.history.replaceState(null, '', '/faculty/students/record-history?section_id=section-1')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, { ...assignment, section_id: 'section-2', section: { ...assignment.section, section_id: 'section-2', name: 'Section B' } }])
    let finish!: (value: { items: FacultyStudentRegistrationEvent[]; total: number }) => void
    vi.mocked(getFacultyStudentRegistrationHistory).mockImplementation((_token, section) => section === 'section-1' ? new Promise((resolve) => { finish = resolve }) : Promise.resolve({ items: [{ ...activity, student_name: 'Section B student' }], total: 1 }))
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByRole('combobox', { name: 'Section and subject' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Section and subject' }), 'section-2')
    expect(await screen.findByText('Section B student')).toBeInTheDocument()
    await act(async () => finish({ items: [activity], total: 1 }))
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/record-history?section_id=section-2')
  })

  it('hides history after an access error, supports retry, and clears it after assignment revocation', async () => {
    window.history.replaceState(null, '', '/faculty/students/record-history?section_id=section-1')
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    vi.mocked(getFacultyStudentRegistrationHistory).mockRejectedValueOnce(new Error('Section access denied'))
    await user.click(screen.getByRole('button', { name: 'Refresh history' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Section access denied')
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByText('Ada Rao')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    await act(async () => { await queryClient.invalidateQueries({ queryKey: ['faculty', 'students', 'token'] }) })
    await waitFor(() => expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument())
  })

  it('keeps the selected page when a registration finishes after leaving the form', async () => {
    let finish!: (student: FacultyAttendanceRosterRow) => void
    vi.mocked(addFacultyAttendanceStudent).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Roster student')
    const nav = screen.getByRole('navigation', { name: 'Students pages' })
    await user.click(within(nav).getByRole('link', { name: 'Register', exact: true }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(screen.getByRole('button', { name: 'Registering student…' })).toBeDisabled()
    await user.click(within(nav).getByRole('link', { name: 'Record history' }))
    await screen.findByText('Added to roster')
    await act(async () => finish(pending))
    expect(window.location.pathname).toBe('/faculty/students/record-history')
    expect(screen.getByRole('region', { name: 'Student registration history' })).toBeInTheDocument()
  })

  it('keeps the pending filter through search, clearing search and pagination', async () => {
    window.history.replaceState(null, '', '/faculty/students/waiting-approval?section_id=section-1')
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [pending], total: 26 })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Beena Shah')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('25'))
    await user.type(screen.getByRole('textbox', { name: 'Search students' }), 'Beena')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe('Beena'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL')
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe(''))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL')
    expect(screen.queryByRole('button', { name: /^(Approve|Reject)$/ })).not.toBeInTheDocument()
  })

  it('shows dedicated empty states and disables Register for a read-only section', async () => {
    window.history.replaceState(null, '', '/faculty/students/waiting-approval?section_id=section-1')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([{ ...assignment, can_manage: false }])
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(getFacultyStudentRegistrationHistory).mockResolvedValue({ items: [], total: 0 })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('No students waiting for approval')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Students pages' })
    expect(within(nav).getByText('Register')).toHaveAttribute('aria-disabled', 'true')
    expect(within(nav).queryByRole('link', { name: 'Register', exact: true })).not.toBeInTheDocument()
    await user.click(within(nav).getByRole('link', { name: 'Record history' }))
    expect(await screen.findByText('No registration activity recorded for this section yet.')).toBeInTheDocument()
  })
})

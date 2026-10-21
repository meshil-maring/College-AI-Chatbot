import './__tests__/FacultyStudents.support.tsx'
import { assignment, student } from './__tests__/FacultyStudents.support.tsx'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceProfile,
  getFacultyAttendanceStudents,
  type FacultyAttendanceRosterRow,
} from '../../../services/faculty/facultyAttendanceApi.ts'
import FacultyStudents from './FacultyStudents.tsx'
describe('FacultyStudents', () => {
  it('searches, filters and sorts on the server and resets pagination for new filters', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 26 })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() =>
      expect(getFacultyAttendanceStudents).toHaveBeenLastCalledWith('token', 'section-1', expect.any(URLSearchParams)),
    )
    await screen.findByText('26–26 of 26 students')
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('25')
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'UNI001')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe('UNI001'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('0')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Registration status' }), 'PENDING_APPROVAL')
    await waitFor(() =>
      expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL'),
    )
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sort by' }), 'student_name')
    await waitFor(() =>
      expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('sort')).toBe('student_name'),
    )
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() =>
      expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].has('registration')).toBe(false),
    )
    expect(screen.getByRole('searchbox', { name: 'Search students' })).toHaveValue('')
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
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'missing')
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
    const second = {
      ...assignment,
      section_id: 'section-2',
      assignment_id: 'section-2',
      section: { ...assignment.section, section_id: 'section-2', name: 'Section B', code: 'B' },
    }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second])
    let finish!: (result: { items: FacultyAttendanceRosterRow[]; total: number }) => void
    vi.mocked(getFacultyAttendanceStudents).mockImplementation((_token, section) =>
      section === 'section-1'
        ? new Promise((resolve) => {
            finish = resolve
          })
        : Promise.resolve({ items: [{ ...student, roster_id: 'roster-2', student_name: 'Beena Shah' }], total: 1 }),
    )
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByRole('combobox', { name: 'Section', exact: true })
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'Ada')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Section', exact: true }), 'B')
    expect(await screen.findByText('Beena Shah')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search students' })).toHaveValue('')
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
    vi.mocked(getFacultyAttendanceProfile).mockResolvedValueOnce({
      student,
      section: assignment.section,
      total: 51,
      history: [{ record_id: 'record-1', session_date: '2026-10-15', status: 'present' }],
    })
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
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({
      items: [
        { ...student, attendance_percentage: null },
        {
          ...student,
          roster_id: 'roster-2',
          student_name: 'Beena Shah',
          attendance_percentage: 0,
          email: null,
          university_roll_number: null,
        },
      ],
      total: 2,
    })
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('No records')).toBeInTheDocument()
    expect(screen.getByText('0.00%')).toBeInTheDocument()
    expect(screen.getByText('Email not recorded')).toBeInTheDocument()
  })

  it('shows the design breadcrumb and roster status cards and filters from a card', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' })
    expect(within(breadcrumb).getByText('Students')).toBeInTheDocument()
    expect(within(breadcrumb).getByText('Roster')).toBeInTheDocument()
    const activeCard = await waitFor(() => {
      const card = screen.getByRole('button', { name: /Active Students/ })
      expect(card).toHaveTextContent('1')
      return card
    })
    expect(screen.getByRole('button', { name: /Pending Approval/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Unregistered Students/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Inactive Students/ })).toBeInTheDocument()
    expect(activeCard).toHaveAttribute('aria-pressed', 'false')
    await user.click(activeCard)
    expect(activeCard).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() =>
      expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('registration')).toBe('ACTIVE'),
    )
  })
})

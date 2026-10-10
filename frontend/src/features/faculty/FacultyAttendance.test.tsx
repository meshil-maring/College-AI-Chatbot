/// <reference types="vitest/globals" />
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyAttendance from './FacultyAttendance.tsx'
import { clearNavigationQueryCache, NAVIGATION_QUERY_POLICY, queryClient } from '../../lib/queryClient.ts'
import { facultyAttendanceKeys } from './useFacultyAttendanceData.ts'
import {
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceRoster,
  uploadFacultyAttendance,
  getFacultyAttendanceStudents,
  getFacultyAttendanceOverview,
  getFacultyAttendanceProfile,
  getFacultyAttendanceImports,
  getFacultyAttendanceSessions,
  getFacultyAttendanceImportReview,
  correctFacultyAttendanceImportRow,
  markFacultyAttendance,
} from '../../services/facultyAttendanceApi.ts'

vi.mock('../../services/facultyAttendanceApi.ts', () => ({
  commitFacultyAttendanceImport: vi.fn(),
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceRoster: vi.fn(),
  markFacultyAttendance: vi.fn(),
  uploadFacultyAttendance: vi.fn(),
  getFacultyAttendanceStudents: vi.fn(),
  getFacultyAttendanceOverview: vi.fn(),
  getFacultyAttendanceProfile: vi.fn(),
  getFacultyAttendanceImports: vi.fn(),
  getFacultyAttendanceSessions: vi.fn(),
  getFacultyAttendanceImportReview: vi.fn(),
  correctFacultyAttendanceImportRow: vi.fn(),
}))

const assignment = {
  assignment_id: 'assignment-1',
  assigned_at: '2026-10-06T00:00:00Z',
  section_id: 'section-1',
  semester_id: 'semester-1',
  academic_year_id: 'year-1',
  can_manage: true,
  section: { section_id: 'section-1', name: 'Section A', code: 'A', course: { name: 'Data Mining', code: 'CS-501' }, department_id: 'dept-1', department: { department_id: 'dept-1', name: 'Computing' }, program_id: 'program-1', program: { program_id: 'program-1', name: 'B.Tech' }, academic_year_id: 'year-1', academic_year: { academic_year_id: 'year-1', name: '2026–27' }, semester_id: 'semester-1', semester: { semester_id: 'semester-1', name: 'Semester 1' } },
}

const roster = [{
  roster_id: 'roster-1',
  register_number: 'CSE23-001',
  university_roll_number: '2023CSE001',
  student_name: 'Rahul Sharma',
  email: 'rahul@example.com',
  address: null,
  roster_status: 'ACTIVE' as const,
  linked_student_id: 'student-1',
  attendance_percentage: 92.86, record_count: 28, present: 26, absent: 2,
  imported_summary: { attendance_percentage: 1, total_classes: 200 },
}]

const overview = { total_students: 1, session_count: 28, present: 26, absent: 2, average_attendance: 92.86, low_attendance_count: 0, monitoring_threshold: 75, trend: [] }

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceRoster).mockResolvedValue(roster)
  vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: roster, total: 1 })
  vi.mocked(getFacultyAttendanceOverview).mockResolvedValue(overview)
  vi.mocked(getFacultyAttendanceImports).mockResolvedValue([])
  vi.mocked(getFacultyAttendanceSessions).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(getFacultyAttendanceProfile).mockResolvedValue({ student: roster[0], section: assignment.section, total: 1, history: [{ record_id: 'record-1', session_date: '2026-10-07', status: 'present' }] })
  vi.mocked(markFacultyAttendance).mockResolvedValue({ session_id: 'session-1', record_count: 1 })
  vi.mocked(uploadFacultyAttendance).mockResolvedValue({ import_id: 'import-1', summary: { total_rows: 1, valid: 1, new_records: 1, updates: 0, errors: 0 }, rows: [{ row_number: 2, normalized_data: { student_name: 'Rahul Sharma' }, validation_status: 'NEW', errors: [] }] })
  vi.mocked(commitFacultyAttendanceImport).mockResolvedValue({ imported_rows: 1 })
})

describe('FacultyAttendance', () => {
  it('renders cached attendance immediately when revisiting without repeating fresh reads', async () => {
    const first = render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    first.unmount()
    render(<FacultyAttendance accessToken="token" />)
    expect(screen.getByText('Rahul Sharma')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Subject' })).toHaveValue('assignment-1')
    expect(screen.queryByText('Loading attendance summary…')).not.toBeInTheDocument()
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(1)
    expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(1)
  })

  it('shows students while a slow overview is still loading', async () => {
    const summary = deferred<typeof overview>()
    vi.mocked(getFacultyAttendanceOverview).mockReturnValueOnce(summary.promise)
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
    expect(screen.getByText('Loading attendance summary…')).toBeInTheDocument()
    await act(async () => summary.resolve(overview))
    await waitFor(() => expect(screen.queryByText('Loading attendance summary…')).not.toBeInTheDocument())
  })

  it.each(['mark', 'upload'] as const)('opens a requested %s workflow on both first entry and a cached visit', async (action) => {
    const title = action === 'mark' ? 'Mark Attendance' : 'Upload Attendance'
    const first = render(<FacultyAttendance accessToken="token" actionRequest={{ action, id: 1 }} />)
    expect(await screen.findByRole('dialog', { name: title })).toBeInTheDocument()
    await screen.findAllByText('Rahul Sharma')
    first.unmount()
    render(<FacultyAttendance accessToken="token" actionRequest={{ action, id: 2 }} />)
    expect(screen.getByRole('dialog', { name: title })).toBeInTheDocument()
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
  })

  it('shows the overview while a slow roster is still loading', async () => {
    const students = deferred<{ items: typeof roster; total: number }>()
    vi.mocked(getFacultyAttendanceStudents).mockReturnValueOnce(students.promise)
    render(<FacultyAttendance accessToken="token" />)
    await waitFor(() => expect(screen.getByText('Classes Conducted').parentElement).toHaveTextContent('28'))
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
    await act(async () => students.resolve({ items: roster, total: 1 }))
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
  })

  it('displays the first roster page before remaining pages and waits for a complete export', async () => {
    const remaining = deferred<{ items: typeof roster; total: number }>()
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValueOnce({ items: roster, total: 2 }).mockReturnValueOnce(remaining.promise)
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
    expect(await screen.findByText(/1 of 2 loaded/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Export/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mark Attendance' })).toBeDisabled()
    await act(async () => remaining.resolve({ items: [{ ...roster[0], roster_id: 'roster-2', student_name: 'Final Student' }], total: 2 }))
    expect(await screen.findByText('Final Student')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Export/ })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Mark Attendance' })).toBeEnabled()
    expect(screen.queryByText(/1 of 2 loaded/)).not.toBeInTheDocument()
  })

  it('keeps cached attendance visible while stale data refreshes on a revisit', async () => {
    const first = render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    first.unmount()
    for (const query of queryClient.getQueryCache().findAll({ queryKey: facultyAttendanceKeys.all('token') })) {
      if (query.state.data !== undefined) queryClient.setQueryData(query.queryKey, query.state.data, {
        updatedAt: Date.now() - NAVIGATION_QUERY_POLICY.staleTime - 1,
      })
    }
    const students = deferred<{ items: typeof roster; total: number }>()
    vi.mocked(getFacultyAttendanceStudents).mockReturnValueOnce(students.promise)
    render(<FacultyAttendance accessToken="token" />)
    expect(screen.getByText('Rahul Sharma')).toBeInTheDocument()
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    expect(screen.getByText('Rahul Sharma')).toBeInTheDocument()
    await act(async () => students.resolve({ items: [{ ...roster[0], student_name: 'Updated Student' }], total: 1 }))
    expect(await screen.findByText('Updated Student')).toBeInTheDocument()
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
  })

  it('skips fresh reads on focus and deduplicates an ongoing stale refresh', async () => {
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(1)
    expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(1)
    for (const query of queryClient.getQueryCache().findAll({ queryKey: facultyAttendanceKeys.all('token') })) {
      if (query.state.data !== undefined) queryClient.setQueryData(query.queryKey, query.state.data, {
        updatedAt: Date.now() - NAVIGATION_QUERY_POLICY.staleTime - 1,
      })
    }
    const students = deferred<{ items: typeof roster; total: number }>()
    vi.mocked(getFacultyAttendanceStudents).mockReturnValueOnce(students.promise)
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Rahul Sharma')).toBeInTheDocument()
    await act(async () => students.resolve({ items: roster, total: 1 }))
    await waitFor(() => expect(screen.queryByText('Refreshing attendance…')).not.toBeInTheDocument())
  })

  it('clears the previous session view immediately when the access token changes', async () => {
    const view = render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    const resources = deferred<typeof assignment[]>()
    vi.mocked(getFacultyAttendanceAssignments).mockReturnValueOnce(resources.promise)
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [{ ...roster[0], student_name: 'New Session Student' }], total: 1 })
    view.rerender(<FacultyAttendance accessToken="new-token" />)
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
    await act(async () => resources.resolve([assignment]))
    expect(await screen.findByText('New Session Student')).toBeInTheDocument()
    expect(getFacultyAttendanceOverview).toHaveBeenLastCalledWith('new-token', 'section-1')
    expect(getFacultyAttendanceStudents).toHaveBeenLastCalledWith('new-token', 'section-1', expect.any(URLSearchParams))
  })

  it('removes attendance and paginated roster caches when the session cache is cleared', async () => {
    const view = render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    view.unmount()
    clearNavigationQueryCache()
    expect(queryClient.getQueryCache().findAll({ queryKey: facultyAttendanceKeys.all('token') })).toHaveLength(0)
    const resources = deferred<typeof assignment[]>()
    vi.mocked(getFacultyAttendanceAssignments).mockReturnValueOnce(resources.promise)
    render(<FacultyAttendance accessToken="token" />)
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
    await act(async () => resources.resolve([assignment]))
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2)
  })

  it('reuses section caches when switching subjects without showing another subject roster', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, {
      ...assignment, assignment_id: 'assignment-2', section_id: 'section-2',
      section: { ...assignment.section, section_id: 'section-2', course: { name: 'Algorithms', code: 'CS-502' } },
    }])
    vi.mocked(getFacultyAttendanceStudents).mockImplementation(async (_token, sectionId) => ({
      items: sectionId === 'section-1' ? roster : [{ ...roster[0], student_name: 'Second Subject Student' }], total: 1,
    }))
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Subject' }), 'assignment-2')
    expect(await screen.findByText('Second Subject Student')).toBeInTheDocument()
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Subject' }), 'assignment-1')
    expect(screen.getByText('Rahul Sharma')).toBeInTheDocument()
    expect(screen.queryByText('Second Subject Student')).not.toBeInTheDocument()
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2)
  })

  it('hides cached records when a refresh rejects a revoked assignment', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'View' }))
    expect(screen.getByRole('dialog', { name: 'Student Attendance Profile' })).toBeInTheDocument()
    vi.mocked(getFacultyAttendanceOverview).mockRejectedValue(new Error('Your teaching assignment is no longer valid'))
    await act(async () => { await queryClient.invalidateQueries({ queryKey: facultyAttendanceKeys.section('token', '', 'section-1') }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Your teaching assignment is no longer valid')
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Attendance' })).toBeDisabled()
  })

  it('renders an honest empty state when the faculty has no assignments', async () => {
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByRole('heading', { name: 'No Active Assignments' })).toBeInTheDocument()
    expect(screen.queryByText('42')).not.toBeInTheDocument()
  })

  it('renders authorized roster data and opens manual attendance', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
    expect(screen.getAllByText('92.86%').length).toBeGreaterThan(0)
    expect(screen.getByRole('combobox', { name: 'Subject' })).toHaveValue('assignment-1')
    expect(screen.getByRole('combobox', { name: 'Department' })).toHaveTextContent('Computing')
    expect(screen.queryByText('1.00%')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    expect(screen.getByRole('dialog', { name: 'Mark Attendance' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Attendance for Rahul Sharma' })).toBeInTheDocument()
  })

  it('bulk marks a roster and permits an individual change before submission', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    await user.click(screen.getByRole('button', { name: 'Mark all present' }))
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), 'absent')
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [{ ...roster[0], attendance_percentage: 89.29, present: 25, absent: 3 }], total: 1 })
    vi.mocked(getFacultyAttendanceOverview).mockResolvedValue({ ...overview, average_attendance: 89.29, present: 25, absent: 3 })
    await user.click(screen.getByRole('button', { name: 'Save Attendance' }))
    await waitFor(() => expect(markFacultyAttendance).toHaveBeenCalledWith('token', 'section-1', expect.any(String), { 'roster-1': 'absent' }))
    expect(await screen.findByText('1 attendance records saved.')).toBeInTheDocument()
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('89.29%')).toBeInTheDocument()
  })

  it('does not submit a student changed back to not marked', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), 'present')
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), '')
    await user.click(screen.getByRole('button', { name: 'Save Attendance' }))
    expect(markFacultyAttendance).not.toHaveBeenCalled()
  })

  it('shows subject-specific profile history from the server', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'View' }))
    const modal = screen.getByRole('dialog', { name: 'Student Attendance Profile' })
    expect(await within(modal).findByText('2026-10-07')).toBeInTheDocument()
    expect(within(modal).getByText(/this subject only/)).toBeInTheDocument()
  })

  it.each(['HOD', 'Class In-Charge'])('keeps %s monitoring read-only', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([{ ...assignment, can_manage: false }])
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    expect(screen.getByText(/Monitoring access/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Attendance' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Upload Attendance' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    expect(await screen.findByText('No imports are available for this subject.')).toBeInTheDocument()
  })

  it('displays real sessions and import history', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceImports).mockResolvedValue([{ import_id: 'import-1', original_filename: 'roster.csv', uploaded_by: 'faculty-1', created_at: '2026-10-07T00:00:00Z', status: 'IMPORTED', summary: { total_rows: 1, imported: 1 } }])
    vi.mocked(getFacultyAttendanceSessions).mockResolvedValue({ items: [{ session_id: 'session-1', session_date: '2026-10-07', record_count: 1, present: 1, absent: 0, attendance_percentage: 100 }], total: 1 })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    expect(await screen.findByText('roster.csv')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Session-wise View' }))
    expect(await screen.findByText('2026-10-07')).toBeInTheDocument()
  })

  it('shows permission denial without stale student data', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockRejectedValue(new Error('Your teaching assignment is no longer valid'))
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Your teaching assignment is no longer valid')
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
  })

  it('refreshes context after revocation and removes the roster', async () => {
    const { rerender } = render(<FacultyAttendance accessToken="token" scopeVersion="initial" />)
    await screen.findByText('Rahul Sharma')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    rerender(<FacultyAttendance accessToken="token" scopeVersion="revoked" />)
    expect(await screen.findByText('No Active Assignments')).toBeInTheDocument()
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
  })

  it('loads every server page instead of truncating at the REST row cap', async () => {
    const first = Array.from({ length: 500 }, (_, index) => ({ ...roster[0], roster_id: `r-${index}`, register_number: `R${index}`, student_name: `Student ${index}` }))
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValueOnce({ items: first, total: 501 }).mockResolvedValueOnce({ items: [{ ...roster[0], student_name: 'Final Student' }], total: 501 })
    render(<FacultyAttendance accessToken="token" />)
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    const args = vi.mocked(getFacultyAttendanceStudents).mock.calls[1]
    expect(args[2].get('offset')).toBe('500')
    expect(await screen.findByText(/of 501 students/)).toBeInTheDocument()
  })

  it.each(['ERROR', 'CONFLICT', 'DUPLICATE'])('blocks committing %s rows', async (state) => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockResolvedValue({ import_id: 'import-1', summary: { total_rows: 2, valid: 1, errors: state === 'ERROR' ? 1 : 0, conflicts: state === 'CONFLICT' ? 1 : 0, duplicates: state === 'DUPLICATE' ? 1 : 0 }, rows: [{ row_number: 2, normalized_data: { student_name: 'Ada' }, validation_status: state, errors: ['Identity issue'] }] })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(screen.getByLabelText('Attendance file'), new File(['data'], 'attendance.csv', { type: 'text/csv' }))
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    await user.click(await screen.findByRole('button', { name: 'Continue to Review' }))
    expect(screen.getByRole('button', { name: 'Import 1 Valid Records' })).toBeDisabled()
    expect(commitFacultyAttendanceImport).not.toHaveBeenCalled()
  })

  it('asks for OCR/AI consent only when the server requires it', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockRejectedValueOnce(Object.assign(new Error('Confirmation required'), { code: 'AI_CONFIRMATION_REQUIRED' }))
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(screen.getByLabelText('Attendance file'), new File(['image'], 'scan.png', { type: 'image/png' }))
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByText('AI Processing May Be Required')).toBeInTheDocument()
    expect(screen.getByText(/AI processing can consume tokens/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() => expect(uploadFacultyAttendance).toHaveBeenLastCalledWith('token', 'section-1', 'semester-1', expect.any(File), true))
  })

  it('shows import network errors and keeps the upload available', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockRejectedValue(new Error('OCR is unavailable; use CSV/XLSX'))
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(screen.getByLabelText('Attendance file'), new File(['data'], 'scan.pdf', { type: 'application/pdf' }))
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByRole('button', { name: 'Process File' })).toBeInTheDocument()
    expect(screen.getAllByText('OCR is unavailable; use CSV/XLSX').length).toBeGreaterThan(0)
  })

  it('revalidates corrected staging values before committing', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockResolvedValue({ import_id: 'import-1', summary: { total_rows: 1, valid: 0, errors: 1 }, rows: [{ row_number: 2, normalized_data: { register_number: 'R1', student_name: 'Ada', attendance_percentage: '200' }, validation_status: 'ERROR', errors: ['Percentage out of range'] }] })
    vi.mocked(correctFacultyAttendanceImportRow).mockResolvedValue({ import_id: 'import-1', status: 'REVIEWED', summary: { total_rows: 1, valid: 1, errors: 0 }, rows: [{ row_number: 2, normalized_data: { register_number: 'R1', student_name: 'Ada', attendance_percentage: '70' }, validation_status: 'NEW', errors: [] }] })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(screen.getByLabelText('Attendance file'), new File(['data'], 'attendance.csv', { type: 'text/csv' }))
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    await user.click(await screen.findByRole('button', { name: 'Continue to Review' }))
    await user.click(screen.getByText('Values / correction'))
    const field = screen.getByLabelText('attendance_percentage row 2')
    await user.clear(field); await user.type(field, '70')
    await user.click(screen.getByRole('button', { name: 'Save correction and validate again' }))
    await waitFor(() => expect(correctFacultyAttendanceImportRow).toHaveBeenCalledWith('token', 'import-1', 2, expect.objectContaining({ attendance_percentage: '70' })))
    expect(await screen.findByRole('button', { name: 'Import 1 Valid Records' })).toBeEnabled()
  })

  it('opens an imported history review without enabling commit', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceImports).mockResolvedValue([{ import_id: 'import-1', original_filename: 'done.csv', uploaded_by: 'faculty-1', created_at: '2026-10-07T00:00:00Z', status: 'IMPORTED', summary: { total_rows: 1, imported: 1 } }])
    vi.mocked(getFacultyAttendanceImportReview).mockResolvedValue({ import_id: 'import-1', status: 'IMPORTED', summary: { total_rows: 1, valid: 1, errors: 0 }, rows: [{ row_number: 2, normalized_data: { student_name: 'Ada' }, validation_status: 'NEW', errors: [] }] })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    await user.click(await screen.findByRole('button', { name: 'Review' }))
    expect(await screen.findByRole('button', { name: 'Already Imported' })).toBeDisabled()
  })

  it('supports keyboard dialog close and restores focus', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    const opener = screen.getByRole('button', { name: 'Mark Attendance' })
    await user.click(opener)
    expect(screen.getByRole('dialog', { name: 'Mark Attendance' })).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(opener).toHaveFocus()
  })

  it('keeps upload review and commit behind the explicit workflow', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'Upload Attendance' }))
    const file = new File(['register_number,student_name\nCSE23-001,Rahul Sharma'], 'attendance.csv', { type: 'text/csv' })
    await user.upload(screen.getByLabelText('Attendance file'), file)
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByText(/File processed successfully/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Required Fields' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Continue to Review' }))
    expect(screen.getByRole('button', { name: 'Import 1 Valid Records' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Import 1 Valid Records' }))
    expect(await screen.findByText('Attendance Imported Successfully')).toBeInTheDocument()
    expect(commitFacultyAttendanceImport).toHaveBeenCalledWith('token', 'import-1')
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
  })
})

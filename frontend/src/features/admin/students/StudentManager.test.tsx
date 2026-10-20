import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentManager from './StudentManager.tsx'
import { adminStudentWorkspaceApi as api } from '../../../services/adminStudentWorkspaceApi.ts'
import { getFacultyAttendanceAssignments, getFacultyAttendanceStudents } from '../../../services/facultyAttendanceApi.ts'
import { listPendingStudents } from '../../../services/adminApi.ts'
import { readStudentFile } from './studentImport.ts'
import type { ClassStudentRegistration } from '../../../services/studentRegistrationApi.ts'

vi.mock('../../../services/adminStudentWorkspaceApi.ts')
vi.mock('../../../services/facultyAttendanceApi.ts')
vi.mock('../../../services/adminApi.ts')
vi.mock('./studentImport.ts', async (original) => ({ ...await original<typeof import('./studentImport.ts')>(), readStudentFile: vi.fn(), downloadCsv: vi.fn() }))
const auth = vi.hoisted(() => ({ accessToken: 'token', user: { institution_id: 'institution-a' as string | null, effective_permissions: ['*'] as string[] } }))
vi.mock('../../auth/AuthProvider.tsx', () => ({ useAuth: () => auth }))
const assignment = { can_manage: true, assignment_id: 'section-1', section_id: 'section-1', assigned_at: '', academic_year_id: 'year-1', semester_id: 'semester-1', section: { section_id: 'section-1', name: 'Section A', code: 'A', program_id: 'program-1', program: { program_id: 'program-1', name: 'Computer Science', degree_type: 'B.Tech' }, course: { name: 'Data Mining', code: 'CS501' } } }
const student = { roster_id: 'roster-1', student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: 'UNI001', email: 'ada@college.test', roster_status: 'ACTIVE' as const, linked_student_id: 'private-student', attendance_percentage: 80 }
const registration: ClassStudentRegistration = { ...student, registration_id: 'registration-1', batch_id: 'batch-1', program_id: 'program-1', section_code: 'A', batch_start_year: 2026, batch_end_year: 2030, identity_conflict: false, subjects_assigned: false }
const props = { section: 'roster' as const, sectionId: '', onNavigate: vi.fn(), registrationMethod: 'individual' as const, onRegistrationMethod: vi.fn() }

beforeEach(() => {
  vi.resetAllMocks()
  auth.user.institution_id = 'institution-a'; auth.user.effective_permissions = ['*']
  vi.mocked(api.getSections).mockResolvedValue([assignment])
  vi.mocked(api.getStudents).mockImplementation(async (_token, _section, query) => query.get('registration') && query.get('registration') !== 'ACTIVE' ? { items: [], total: 0 } : { items: [student], total: 1 })
  vi.mocked(api.getRegistrations).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(api.getBatches).mockResolvedValue([{ batch_id: 'batch-1', program_id: 'program-1', start_year: 2026, end_year: 2030, is_active: true }])
  vi.mocked(api.createRegistration).mockResolvedValue(registration)
  vi.mocked(api.getHistory).mockResolvedValue({ items: [{ event_id: 'event-1', roster_id: 'roster-1', occurred_at: '2026-10-20T08:00:00Z', action: 'roster_added', student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: 'UNI001' }], total: 1 })
  vi.mocked(api.getProfile).mockResolvedValue({ student, section: assignment.section, total: 1, history: [{ record_id: 'record-1', session_date: '2026-10-19', status: 'present' }] })
  vi.mocked(listPendingStudents).mockResolvedValue([])
})

describe('Admin uses the full Faculty Students workflow', () => {
  it('applies and clears an admission cohort across both roster lists through Admin endpoints', async () => {
    const user = userEvent.setup()
    render(<StudentManager {...props} />)
    await screen.findByText('Ada Rao')
    for (const name of ['Course', 'Branch', 'Batch', 'Section', 'Semester']) expect(screen.getByRole('combobox', { name, exact: true })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('batch_id')).toBe('batch-1'))
    expect(api.getRegistrations).toHaveBeenLastCalledWith('token', 'section-1', 0, 25, undefined, { batchId: 'batch-1', search: '', sort: 'register_number' })
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('search')).toBe('Ada'))
    expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('batch_id')).toBe('batch-1')
    expect(api.getRegistrations).toHaveBeenLastCalledWith('token', 'section-1', 0, 25, undefined, { batchId: 'batch-1', search: 'Ada', sort: 'register_number' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), '')
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].has('batch_id')).toBe(false))
    expect(screen.getByRole('searchbox', { name: 'Search students' })).toHaveValue('Ada')
    expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('search')).toBe('Ada')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByRole('combobox', { name: 'Batch' })).toHaveValue('')
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].has('batch_id')).toBe(false))
    expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
  })

  it('provides roster search, sorting, details and attendance through Admin endpoints', async () => {
    const user = userEvent.setup()
    render(<StudentManager {...props} />)
    await screen.findByText('Ada Rao')
    expect(screen.getByRole('button', { name: /Active Students/ })).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('search')).toBe('Ada'))
    await user.click(screen.getByRole('button', { name: 'View Ada Rao' }))
    expect(await screen.findByText('Subject attendance history')).toBeInTheDocument()
    expect(api.getProfile).toHaveBeenCalledWith('token', 'roster-1', 0)
    expect(screen.queryByText('private-student')).not.toBeInTheDocument()
    expect(getFacultyAttendanceAssignments).not.toHaveBeenCalled()
    expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
  })
  it('saves an individual student with course, branch, section and a configured batch', async () => {
    const user = userEvent.setup()
    render(<StudentManager {...props} section="register" />)
    await screen.findByRole('textbox', { name: 'Student name (required)' })
    expect(screen.getByRole('combobox', { name: 'Course' })).toHaveDisplayValue('B.Tech')
    expect(screen.getByRole('combobox', { name: 'Branch' })).toHaveDisplayValue('Computer Science')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Ada Rao')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(api.createRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section-1', { student_name: 'Ada Rao', register_number: 'CS001', batch_id: 'batch-1' }))
    expect(props.onNavigate).toHaveBeenCalledWith('roster', 'section-1', true)
  })
  it('validates a bulk file, saves selected students and retries only failed saves', async () => {
    vi.mocked(readStudentFile).mockResolvedValue([
      { row: 2, name: 'Ben Rao', registerNumber: 'CS002', rollNumber: '', email: '', attendance: '' },
      { row: 3, name: 'Casey Rao', registerNumber: 'CS003', rollNumber: '', email: '', attendance: '' },
    ])
    vi.mocked(api.createRegistration).mockResolvedValueOnce(registration).mockRejectedValueOnce(new Error('Temporary registration failure')).mockResolvedValue(registration)
    const user = userEvent.setup()
    render(<StudentManager {...props} section="register" registrationMethod="bulk" />)
    await screen.findByRole('combobox', { name: 'Batch' })
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    fireEvent.change(screen.getByLabelText('Choose student file'), { target: { files: [new File(['content'], 'students.csv')] } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue to Import' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    await user.click(screen.getByRole('button', { name: 'Register 2 students' }))
    const results = await screen.findByRole('region', { name: 'Registration results' })
    expect(within(results).getByRole('status')).toHaveTextContent(/Registered: 1.*Failed: 1/)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry failed registrations' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Retry failed registrations' }))
    await waitFor(() => expect(within(results).getByRole('status')).toHaveTextContent(/Registered: 2.*Failed: 0/))
    expect(api.createRegistration).toHaveBeenCalledTimes(3)
    expect(vi.mocked(api.createRegistration).mock.lastCall?.[2].student_name).toBe('Casey Rao')
  })
  it('shows section history rather than an actor-limited audit preview', async () => {
    render(<StudentManager {...props} section="history" />)
    expect(await screen.findByText('Added to roster')).toBeInTheDocument()
    expect(api.getHistory).toHaveBeenCalledWith('token', 'section-1', expect.any(URLSearchParams))
  })
  it('keeps both the section waiting list and account approval actions', async () => {
    render(<StudentManager {...props} section="waiting-approval" />)
    expect(await screen.findByRole('heading', { name: 'Pending registrations' })).toBeInTheDocument()
    await waitFor(() => expect(vi.mocked(api.getStudents).mock.lastCall?.[2].get('registration')).toBe('PENDING_APPROVAL'))
    expect(listPendingStudents).toHaveBeenCalledWith('token')
  })
  it('does not read academic records without attendance access or institution scope', () => {
    auth.user.effective_permissions = ['students.read']
    const view = render(<StudentManager {...props} section="history" />)
    expect(screen.getByRole('status')).toHaveTextContent('does not have permission')
    expect(api.getHistory).not.toHaveBeenCalled()
    expect(api.getSections).not.toHaveBeenCalled()
    auth.user.institution_id = null
    view.rerender(<StudentManager {...props} />)
    expect(screen.getByRole('status')).toHaveTextContent('No institution is linked')
  })
  it('explains Academic Setup when no active sections are available for registration', async () => {
    vi.mocked(api.getSections).mockResolvedValue([])
    render(<StudentManager {...props} section="register" />)
    expect(await screen.findByText('Create active sections in Academic Setup before managing student rosters.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh sections' })).toBeInTheDocument()
    expect(api.createRegistration).not.toHaveBeenCalled()
  })
})

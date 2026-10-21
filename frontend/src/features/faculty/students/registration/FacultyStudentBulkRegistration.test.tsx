import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyStudentRegistration from './FacultyStudentRegistration.tsx'
import { AdminApiError } from '../../../../services/admin/adminApi.ts'
import { createClassStudentRegistration, getClassStudentRegistrations, getRegistrationBatches, type ClassStudentRegistration } from '../../../../services/students/studentRegistrationApi.ts'
import * as files from '../../../admin/students/studentImport.ts'

vi.mock('../../../../services/students/studentRegistrationApi.ts', () => ({ createClassStudentRegistration: vi.fn(), getClassStudentRegistrations: vi.fn(), getRegistrationBatches: vi.fn() }))
vi.mock('../../../admin/students/studentImport.ts', async (original) => ({
  ...await original<typeof import('../../../admin/students/studentImport.ts')>(), readStudentFile: vi.fn(), downloadCsv: vi.fn(),
}))
const assignment = { can_manage: true, assignment_id: 'a1', section_id: 'section-1', assigned_at: '', semester_id: 's1', academic_year_id: 'y1', section: { section_id: 'section-1', name: 'Section A', code: 'A', program_id: 'program-1', program: { program_id: 'program-1', name: 'Computer Science', degree_type: 'B.Tech' }, course: { name: 'Data Mining', code: 'CS501' } } }
const existing: ClassStudentRegistration = { registration_id: 'r1', batch_id: 'batch-1', program_id: 'program-1', section_code: 'A', batch_start_year: 2026, batch_end_year: 2030, identity_conflict: false, subjects_assigned: false, student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: 'UNI001', email: 'ada@example.test', roster_status: 'ACTIVE', linked_student_id: 'student-1' }
const rows: files.ImportStudent[] = [
  { row: 2, name: 'Ben Shah', registerNumber: 'CS002', rollNumber: 'UNI002', email: 'student@college.edu', attendance: '' },
  { row: 3, name: 'Casey Rao', registerNumber: 'CS003', rollNumber: 'UNI003', email: 'student@college.edu', attendance: '' },
  { row: 4, name: 'Ada Rao', registerNumber: 'CS001', rollNumber: 'UNI001', email: 'ada@example.test', attendance: '' },
  { row: 5, name: '', registerNumber: 'CS004', rollNumber: '', email: 'student@college.edu', attendance: '' },
  { row: 6, name: 'Different Student', registerNumber: 'CS001', rollNumber: 'UNI001', email: 'student@college.edu', attendance: '' },
]

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getRegistrationBatches).mockResolvedValue([{ batch_id: 'batch-1', program_id: 'program-1', start_year: 2026, end_year: 2030, is_active: true }])
  vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [existing], total: 1 })
  vi.mocked(files.readStudentFile).mockResolvedValue(rows)
  vi.mocked(createClassStudentRegistration).mockResolvedValue(existing)
})

function setup() {
  const onCancel = vi.fn()
  const view = render(<FacultyStudentRegistration token="token" assignment={assignment} assignments={[assignment]} onSectionChange={vi.fn()} onRegistered={vi.fn()} onCancel={onCancel} />)
  return { ...view, onCancel, user: userEvent.setup() }
}

async function upload() {
  fireEvent.click(screen.getByRole('tab', { name: 'Bulk Registration' }))
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
  fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
  fireEvent.change(screen.getByLabelText('Choose student file'), { target: { files: [new File(['content'], 'students.csv', { type: 'text/csv' })] } })
  await screen.findByText('students.csv')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Continue to Import' })).toBeEnabled())
}

describe('registration methods and bulk import', () => {
  it('explains missing batches and loads newly configured batches when refreshed', async () => {
    const savedBatches = [{ batch_id: 'batch-1', program_id: 'program-1', start_year: 2026, end_year: 2030, is_active: true }]
    vi.mocked(getRegistrationBatches).mockResolvedValueOnce([]).mockResolvedValue(savedBatches)
    const { user } = setup()
    await screen.findByText(/No active batches are set up/)
    expect(screen.getByRole('combobox', { name: 'Batch' })).toBeDisabled()
    expect(screen.getByText(/Academic Setup → Batches/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Refresh batches' }))
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), '2026–2030')
    expect(screen.getByRole('combobox', { name: 'Batch' })).toHaveValue('batch-1')
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
  })

  it('requires an admission batch and never selects a subject when registering an individual student', async () => {
    const { user } = setup()
    expect(screen.getByRole('combobox', { name: 'Course' })).toHaveDisplayValue('B.Tech')
    expect(screen.getByRole('combobox', { name: 'Branch' })).toHaveDisplayValue('Computer Science')
    expect(screen.queryByRole('combobox', { name: /subject/i })).not.toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Ada Rao')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('active batch')
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(createClassStudentRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section-1', {
      student_name: 'Ada Rao', register_number: 'CS001', batch_id: 'batch-1', email: 'beena@college.edu',
    }))
  })
  it('switches accessible tabs with the keyboard and retains the individual form draft', async () => {
    const { user } = setup()
    const individual = screen.getByRole('tab', { name: 'Individual Registration' })
    expect(individual).toHaveAttribute('aria-selected', 'true')
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Draft student')
    individual.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Bulk Registration' })).toHaveFocus()
    expect(screen.getByRole('heading', { name: 'Bulk Student Import' })).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Import progress' })).getAllByRole('listitem')).toHaveLength(4)
    await user.keyboard('{Home}')
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('Draft student')
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
  })

  it('previews four validation groups, confirms only valid rows, and retries failures without repeating successes', async () => {
    const { user, onCancel } = setup()
    await upload()
    const filters = screen.getByRole('group', { name: 'Validation status' })
    for (const label of ['Valid (2)', 'Duplicate (1)', 'Invalid (1)', 'Conflicting (1)']) expect(within(filters).getByRole('button', { name: label })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Select Ada Rao' })).toBeDisabled()
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    expect(screen.getByRole('heading', { name: '2 records selected for import' })).toBeInTheDocument()
    vi.mocked(createClassStudentRegistration).mockResolvedValueOnce(existing).mockRejectedValueOnce(new Error('Temporary registration error'))
    await user.dblClick(screen.getByRole('button', { name: 'Register 2 students' }))
    const results = await screen.findByRole('region', { name: 'Registration results' })
    expect(within(results).getByRole('status')).toHaveTextContent('Registered: 1 · Failed: 1 · Skipped: 3')
    expect(createClassStudentRegistration).toHaveBeenCalledTimes(2)
    expect(createClassStudentRegistration).toHaveBeenNthCalledWith(1, 'token', 'section-1', { student_name: 'Ben Shah', register_number: 'CS002', university_roll_number: 'UNI002', email: 'student@college.edu', batch_id: 'batch-1' })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry failed registrations' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Retry failed registrations' }))
    await waitFor(() => expect(within(results).getByRole('status')).toHaveTextContent('Registered: 2 · Failed: 0 · Skipped: 3'))
    expect(createClassStudentRegistration).toHaveBeenCalledTimes(3)
    expect(vi.mocked(createClassStudentRegistration).mock.lastCall?.[2].student_name).toBe('Casey Rao')
    await user.click(screen.getByRole('button', { name: 'Download Validation Report' }))
    expect(vi.mocked(files.downloadCsv).mock.lastCall?.[1].flat()).toContain('imported')
    await user.click(screen.getByRole('button', { name: 'View Students' }))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('blocks confirmation until the full roster is available and lets the user retry failed checks', async () => {
    vi.mocked(getClassStudentRegistrations).mockRejectedValue(new Error('Roster access unavailable'))
    const { user } = setup()
    await user.click(screen.getByRole('tab', { name: 'Bulk Registration' }))
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await screen.findByText('Roster access unavailable')
    fireEvent.change(screen.getByLabelText('Choose student file'), { target: { files: [new File([], 'students.csv')] } })
    await screen.findByText('students.csv')
    expect(screen.getByRole('button', { name: 'Continue to Import' })).toBeDisabled()
    vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [existing], total: 1 })
    await user.click(screen.getByRole('button', { name: 'Retry roster checks' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue to Import' })).toBeEnabled())
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
  })

  it('stops sending registrations if the server revokes permission', async () => {
    vi.mocked(createClassStudentRegistration).mockRejectedValue(new AdminApiError(403, 'Section permission was revoked'))
    const { user } = setup()
    await upload()
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    await user.click(screen.getByRole('button', { name: 'Register 2 students' }))
    const results = await screen.findByRole('region', { name: 'Registration results' })
    expect(within(results).getByRole('status')).toHaveTextContent('Registered: 0 · Failed: 2')
    expect(createClassStudentRegistration).toHaveBeenCalledOnce()
    expect(within(results).getByText('Not attempted: Section permission was revoked')).toBeInTheDocument()
  })

  it('stops the remaining bulk registrations when the selected batch is archived', async () => {
    vi.mocked(createClassStudentRegistration).mockRejectedValue(new AdminApiError(422, 'The selected batch is unavailable', undefined, 'BATCH_UNAVAILABLE'))
    const { user } = setup()
    await upload()
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    await user.click(screen.getByRole('button', { name: 'Register 2 students' }))
    const results = await screen.findByRole('region', { name: 'Registration results' })
    expect(within(results).getByRole('status')).toHaveTextContent('Registered: 0 · Failed: 2')
    expect(createClassStudentRegistration).toHaveBeenCalledOnce()
    expect(within(results).getByText('Not attempted: The selected batch is unavailable')).toBeInTheDocument()
  })

  it('locks section changes while importing and stops new requests after leaving the page', async () => {
    let finish!: (student: ClassStudentRegistration) => void
    vi.mocked(createClassStudentRegistration).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const { user, unmount } = setup()
    await upload()
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    await user.click(screen.getByRole('button', { name: 'Register 2 students' }))
    expect(screen.getByRole('tab', { name: 'Individual Registration' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Replace File' })).toBeDisabled()
    unmount()
    await act(async () => finish(existing))
    expect(createClassStudentRegistration).toHaveBeenCalledOnce()
  })
})

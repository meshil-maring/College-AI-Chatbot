import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FacultyTests from './FacultyTests.tsx'
import * as api from '../../services/facultyTestsApi.ts'
import type { MarksDetail, TestImport } from '../../services/facultyTestsApi.ts'

vi.mock('../../services/facultyTestsApi.ts')

const scope = { section_id: 'section-1', name: 'Section A', code: 'A', semester_id: 'semester-1',
  department_id: 'department-1', program_id: 'program-1', academic_year_id: 'year-1', can_manage: true,
  department: { department_id: 'department-1', name: 'CSE' }, program: { program_id: 'program-1', name: 'B.Tech' },
  academic_year: { academic_year_id: 'year-1', name: '2026–27' }, semester: { semester_id: 'semester-1', name: 'Semester 5' },
  course: { name: 'Data Mining', code: 'DM' } }
const detail: MarksDetail = {
  test: { test_id: 'test-1', section_id: scope.section_id, title: 'Class test', test_type: 'class_test',
    description: 'Assessment instructions', max_marks: 100, passing_marks: 40, scheduled_date: '2026-10-07', start_time: null,
    end_time: null, duration_minutes: null, status: 'COMPLETED', marks_state: 'DRAFT', version: 3,
    created_by: 'faculty-1', created_at: '2026-10-07T08:00:00Z', updated_at: '2026-10-07T08:00:00Z', can_manage: true, section: scope },
  rows: [{ roster_id: 'roster-1', register_number: 'R1', university_roll_number: 'U1', student_name: 'Ada Student',
    roster_status: 'ACTIVE', reconciliation_state: 'LINKED', mark_status: 'present', scored_marks: 75, percentage: 75, outcome: 'pass', remarks: null },
  { roster_id: 'roster-2', register_number: 'R2', university_roll_number: null, student_name: 'Grace Student',
    roster_status: 'UNREGISTERED', reconciliation_state: 'NONE', mark_status: 'absent', scored_marks: null, percentage: null, outcome: null, remarks: null }],
  review: { total: 2, entered: 2, missing: 0, absent: 1, exempt: 0, not_attempted: 0, conflicts: 0, pass: 1, fail: 0, average_percentage: 75 },
}
const imported: TestImport = { import_id: 'import-1', test_id: 'test-1', original_filename: 'marks.csv', uploaded_by: 'faculty-1',
  status: 'VALIDATED', updated_at: '2026-10-07T08:30:00Z', created_at: '2026-10-07T08:30:00Z', summary: { valid: 1, errors: 0, total_rows: 1 },
  rows: [{ row_number: 2, raw_data: { register_number: 'R1', mark_status: 'present', scored_marks: '90' },
    normalized_data: { register_number: 'R1', mark_status: 'present', scored_marks: '90' }, validation_status: 'VALID', errors: [], warnings: [] }],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getTestResources).mockResolvedValue([scope])
  vi.mocked(api.getTestTypes).mockResolvedValue([{ code: 'class_test', name: 'Class Test' }])
  vi.mocked(api.getTests).mockResolvedValue({ items: [detail.test], total: 1,
    overview: { upcoming: 0, draft: 0, completed: 1, pending_marks: 1, published: 0, locked: 0 } })
  vi.mocked(api.getTest).mockResolvedValue(structuredClone(detail))
  vi.mocked(api.createTest).mockResolvedValue({ ...detail.test, status: 'DRAFT', version: 1 })
  vi.mocked(api.transitionTest).mockResolvedValue(detail.test)
  vi.mocked(api.saveTestMarks).mockResolvedValue({ version: 4 })
  vi.mocked(api.uploadTestMarks).mockResolvedValue(structuredClone(imported))
  vi.mocked(api.correctTestImport).mockResolvedValue(structuredClone(imported))
  vi.mocked(api.commitTestImport).mockResolvedValue({ version: 4 })
  vi.mocked(api.getTestImport).mockResolvedValue({ ...imported, status: 'IMPORTED' })
  vi.mocked(api.getTestHistory).mockResolvedValue({ imports: [], events: [] })
})

async function open() {
  const user = userEvent.setup()
  render(<FacultyTests accessToken="token" />)
  await user.click(await screen.findByRole('button', { name: 'Open Class test' }))
  await screen.findByRole('heading', { name: 'Result review' })
  return user
}

describe('Faculty assessment workspace', () => {
  it('loads real dashboard counts and all academic selectors', async () => {
    render(<FacultyTests accessToken="token" />)
    await screen.findByRole('button', { name: 'Open Class test' })
    expect(api.getTests).toHaveBeenCalledWith('token', 'section-1', 0)
    for (const name of ['Department', 'Program', 'Academic Year', 'Semester', 'Section/Class', 'Subject']) expect(screen.getByRole('combobox', { name })).toBeInTheDocument()
    expect(screen.getByText('Pending mark entry')).toBeInTheDocument()
  })

  it('shows an honest empty assessment state', async () => {
    vi.mocked(api.getTests).mockResolvedValue({ items: [], total: 0, overview: {} })
    render(<FacultyTests accessToken="token" />)
    expect(await screen.findByText('No tests yet for this subject and section.')).toBeInTheDocument()
  })

  it('handles missing authorized scopes without querying tests', async () => {
    vi.mocked(api.getTestResources).mockResolvedValue([])
    render(<FacultyTests accessToken="token" />)
    expect(await screen.findByRole('heading', { name: 'No authorized assessment scopes' })).toBeInTheDocument()
    expect(api.getTests).not.toHaveBeenCalled()
  })

  it('announces loading and resource failures', async () => {
    vi.mocked(api.getTestResources).mockRejectedValue(new Error('Scope unavailable'))
    render(<FacultyTests accessToken="token" />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading assessments')
    expect(await screen.findByRole('alert')).toHaveTextContent('Scope unavailable')
  })

  it('creates a draft with the selected authorized section', async () => {
    const user = userEvent.setup()
    render(<FacultyTests accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'Create Test' }))
    await user.type(screen.getByRole('textbox', { name: 'Title' }), 'Internal assessment')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(api.createTest).toHaveBeenCalledWith('token', 'section-1', expect.objectContaining({ title: 'Internal assessment', max_marks: 100, test_type: 'class_test' })))
    expect(api.transitionTest).not.toHaveBeenCalled()
  })

  it('schedules explicitly after draft creation', async () => {
    const user = userEvent.setup()
    render(<FacultyTests accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'Create Test' }))
    await user.type(screen.getByRole('textbox', { name: 'Title' }), 'Scheduled test')
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-10-08' } })
    await user.click(screen.getByRole('button', { name: 'Save and schedule' }))
    await waitFor(() => expect(api.transitionTest).toHaveBeenCalledWith('token', expect.objectContaining({ version: 1 }), 'schedule'))
  })

  it('saves several edited rows in one batch and preserves absence versus zero', async () => {
    const user = await open()
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Marks for R1' }), { target: { value: '0' } })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Status for R2' }), 'exempt')
    expect(screen.getByText(/2 unsaved rows/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit reviewed marks' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Save marks' }))
    await waitFor(() => expect(api.saveTestMarks).toHaveBeenCalledTimes(1))
    expect(api.saveTestMarks).toHaveBeenCalledWith('token', expect.objectContaining({ version: 3 }), [
      { roster_id: 'roster-1', mark_status: 'present', scored_marks: 0, remarks: null },
      { roster_id: 'roster-2', mark_status: 'exempt', scored_marks: null, remarks: null },
    ], undefined)
    await screen.findByText('Marks saved atomically.')
  })

  it.each(['101', '-1', '1.234'])('blocks invalid marks %s before batch save', async (value) => {
    await open()
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Marks for R1' }), { target: { value } })
    expect(screen.getByRole('alert')).toHaveTextContent('Present requires marks')
    expect(screen.getByRole('button', { name: 'Save marks' })).toBeDisabled()
    expect(api.saveTestMarks).not.toHaveBeenCalled()
  })

  it('protects unsaved changes on navigation and browser unload', async () => {
    const user = await open()
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Marks for R1' }), { target: { value: '80' } })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await user.click(screen.getByRole('button', { name: 'My Tests' }))
    expect(screen.getByRole('heading', { name: 'Result review' })).toBeInTheDocument()
    expect(confirm).toHaveBeenCalledWith('Discard unsaved assessment changes?')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    confirm.mockRestore()
  })

  it('moves between marks inputs with Enter', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, rows: detail.rows.map(r => ({ ...r, mark_status: 'present', scored_marks: 50 })) })
    await open()
    const first = screen.getByRole('spinbutton', { name: 'Marks for R1' })
    first.focus(); fireEvent.keyDown(first, { key: 'Enter' })
    expect(screen.getByRole('spinbutton', { name: 'Marks for R2' })).toHaveFocus()
  })

  it('paginates the authorized roster', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, rows: Array.from({ length: 26 }, (_, i) => ({ ...detail.rows[0]!, roster_id: `r-${i}`, register_number: `R${i + 1}` })) })
    const user = await open()
    expect(screen.queryByRole('spinbutton', { name: 'Marks for R26' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next students' }))
    expect(screen.getByRole('spinbutton', { name: 'Marks for R26' })).toBeInTheDocument()
  })

  it('requires complete reviewed marks before submission', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, review: { ...detail.review, missing: 1 } })
    await open()
    expect(screen.getByRole('button', { name: 'Submit reviewed marks' })).toBeDisabled()
    expect(screen.getByText(/Resolve missing marks/)).toBeInTheDocument()
  })

  it('submits reviewed marks explicitly', async () => {
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Submit reviewed marks' }))
    await waitFor(() => expect(api.transitionTest).toHaveBeenCalledWith('token', detail.test, 'submit'))
  })

  it('publishes submitted results explicitly and keeps marks read-only', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, test: { ...detail.test, marks_state: 'SUBMITTED' } })
    const user = await open()
    expect(screen.getByRole('spinbutton', { name: 'Marks for R1' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Publish results' }))
    await waitFor(() => expect(api.transitionTest).toHaveBeenCalledWith('token', expect.anything(), 'publish'))
  })

  it('locks published results explicitly', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, test: { ...detail.test, status: 'PUBLISHED', marks_state: 'SUBMITTED' } })
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Lock results' }))
    await waitFor(() => expect(api.transitionTest).toHaveBeenCalledWith('token', expect.anything(), 'lock'))
  })

  it('requires a reason for locked corrections and sends the explicit command', async () => {
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, test: { ...detail.test, status: 'LOCKED', marks_state: 'SUBMITTED' } })
    const user = await open()
    expect(screen.getByRole('spinbutton', { name: 'Marks for R1' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Request a controlled correction' }))
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Marks for R1' }), { target: { value: '80' } })
    expect(screen.getByRole('button', { name: 'Save audited correction' })).toBeDisabled()
    await user.type(screen.getByRole('textbox', { name: /Correction reason/ }), 'Verified transcription correction')
    await user.click(screen.getByRole('button', { name: 'Save audited correction' }))
    await waitFor(() => expect(api.saveTestMarks).toHaveBeenCalledWith('token', expect.objectContaining({ status: 'LOCKED' }), expect.anything(), 'Verified transcription correction'))
  })

  it.each(['HOD', 'Class In-Charge'])('keeps %s monitoring read-only', async () => {
    vi.mocked(api.getTestResources).mockResolvedValue([{ ...scope, can_manage: false }])
    vi.mocked(api.getTest).mockResolvedValue({ ...detail, test: { ...detail.test, can_manage: false } })
    const user = await open()
    expect(screen.queryByRole('button', { name: 'Create Test' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Submit reviewed marks' })).not.toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: 'Marks for R1' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'History' }))
    expect(await screen.findByRole('heading', { name: 'Import & assessment history' })).toBeInTheDocument()
  })

  it('clears private results when scope is revoked', async () => {
    const user = await open()
    vi.mocked(api.getTest).mockRejectedValue(new Error('Teaching assignment revoked'))
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Teaching assignment revoked')
    expect(screen.queryByText('Ada Student')).not.toBeInTheDocument()
  })

  it('clears old workflow when authenticated scope changes', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<FacultyTests accessToken="token" scopeVersion="old" />)
    await user.click(await screen.findByRole('button', { name: 'Open Class test' }))
    await screen.findByText('Ada Student')
    vi.mocked(api.getTestResources).mockResolvedValue([])
    rerender(<FacultyTests accessToken="token" scopeVersion="revoked" />)
    await screen.findByRole('heading', { name: 'No authorized assessment scopes' })
    expect(screen.queryByText('Ada Student')).not.toBeInTheDocument()
  })

  it('stages spreadsheets then requires explicit commit', async () => {
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Import' }))
    await user.upload(screen.getByLabelText('Choose marks spreadsheet'), new File(['register_number,mark_status,scored_marks\nR1,present,90'], 'marks.csv', { type: 'text/csv' }))
    await screen.findByRole('button', { name: 'Import reviewed marks' })
    expect(api.commitTestImport).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Import reviewed marks' }))
    await waitFor(() => expect(api.commitTestImport).toHaveBeenCalledWith('token', expect.objectContaining({ import_id: 'import-1' }), detail.test))
    expect(await screen.findByText('Import completed. This review is read-only.')).toBeInTheDocument()
  })

  it('shows blocking import conflicts and permits revalidation', async () => {
    vi.mocked(api.uploadTestMarks).mockResolvedValue({ ...imported, rows: [{ ...imported.rows[0]!, validation_status: 'CONFLICT', errors: ['Conflicting identifiers'] }] })
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Import' }))
    await user.upload(screen.getByLabelText('Choose marks spreadsheet'), new File(['bad'], 'marks.csv', { type: 'text/csv' }))
    expect(await screen.findByText('Conflicting identifiers')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import reviewed marks' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Correct row 2' }))
    await user.click(screen.getByRole('button', { name: 'Revalidate row' }))
    await waitFor(() => expect(api.correctTestImport).toHaveBeenCalled())
    expect(screen.getByRole('button', { name: 'Import reviewed marks' })).toBeEnabled()
  })

  it('shows failed extraction without committing marks', async () => {
    vi.mocked(api.uploadTestMarks).mockRejectedValue(new Error('Malformed workbook'))
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Import' }))
    await user.upload(screen.getByLabelText('Choose marks spreadsheet'), new File(['bad'], 'marks.csv', { type: 'text/csv' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Malformed workbook')
    expect(api.commitTestImport).not.toHaveBeenCalled()
  })

  it('shows correction history and uploader without rendering uploaded HTML', async () => {
    vi.mocked(api.getTestHistory).mockResolvedValue({ imports: [imported], events: [{ action: 'test.marks.post_lock_correct', actor_user_id: 'faculty-1', performed_at: '2026-10-07T08:00:00Z', record_data: { before: 75, after: 80, reason: '<script>alert(1)</script>' } }] })
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'History' }))
    await screen.findByText(/test.marks.post_lock_correct/)
    expect(screen.getByText(/Uploader faculty-1/)).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Review import' }))
    expect(await screen.findByText('Import completed. This review is read-only.')).toBeInTheDocument()
  })

  it('filters student search without changing identity or marks', async () => {
    const user = await open()
    await user.type(screen.getByRole('textbox', { name: 'Find student' }), 'Grace')
    const table = screen.getByRole('table', { name: 'Assessment marks roster' })
    expect(within(table).getByText('Grace Student')).toBeInTheDocument()
    expect(within(table).queryByText('Ada Student')).not.toBeInTheDocument()
  })
})

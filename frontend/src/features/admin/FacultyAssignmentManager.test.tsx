import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyAssignmentManager from './FacultyAssignmentManager.tsx'
import * as api from '../../services/adminApi.ts'
import { responsibilityManagementFixture } from '../../test/facultyResponsibilitiesFixtures.ts'

vi.mock('../../services/adminApi.ts')

const assignmentData = {
  sections: [{
    section_id: 'section-1',
    name: 'Section A',
    code: 'A',
    course: { name: 'Mathematics', code: 'MATH101' },
  }],
  faculty: [{
    id: 'faculty-1',
    email: 'faculty@example.test',
    first_name: 'Ada',
    last_name: 'Lovelace',
  }],
  assignments: [{
    assignment_id: 'assignment-1',
    faculty_user_id: 'faculty-1',
    section_id: 'section-1',
    start_at: '2000-01-01T00:00:00Z',
    end_at: null,
    is_active: true,
    faculty: { email: 'faculty@example.test', first_name: 'Ada', last_name: 'Lovelace' },
    section: { name: 'Section A', code: 'A', course: { name: 'Mathematics', code: 'MATH101' } },
  }],
}

describe('FacultyAssignmentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.getFacultyAssignments).mockResolvedValue(assignmentData)
    vi.mocked(api.createFacultyAssignment).mockResolvedValue({ assignment_id: 'assignment-2' })
    vi.mocked(api.revokeFacultyAssignment).mockResolvedValue({ assignment_id: 'assignment-1' })
    vi.mocked(api.updateFacultyTeachingValidity).mockResolvedValue({ assignment_id: 'assignment-1' })
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({ faculty: assignmentData.faculty, definitions: [], departments: [], sections: [], responsibilities: [] })
  })

  it('creates a selected active faculty-section assignment', async () => {
    vi.mocked(api.createFacultyAssignment).mockResolvedValue({ assignment_id: 'assignment-2' })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    await waitFor(() => {
      expect(api.createFacultyAssignment).toHaveBeenCalledWith('jwt', {
        faculty_user_id: 'faculty-1',
        section_id: 'section-1',
      })
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Faculty section assignment saved.')
    await waitFor(() => expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2))
  })

  it('surfaces assignment failures and does not claim success', async () => {
    vi.mocked(api.createFacultyAssignment).mockRejectedValue(new Error('Section is not active'))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Section is not active')
    expect(screen.queryByText('Faculty section assignment saved.')).not.toBeInTheDocument()
  })

  it('shows a database availability error and clears it after a successful retry', async () => {
    vi.mocked(api.getFacultyAssignments).mockRejectedValueOnce(new Error(
      'Faculty assignments and responsibilities are unavailable until the database update is applied. Please contact your administrator.',
    ))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database update')
    expect(screen.queryByRole('button', { name: 'Assign section' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retry loading assignments' }))
    expect(await screen.findByRole('button', { name: 'Assign section' })).toBeEnabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2)
    expect(api.createFacultyAssignment).not.toHaveBeenCalled()
  })

  it('keeps existing assignments visible during a manual refresh', async () => {
    let resolve!: (data: typeof assignmentData) => void
    vi.mocked(api.getFacultyAssignments).mockResolvedValueOnce(assignmentData).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh assignments' }))
    expect(await screen.findByText('Updating Faculty assignments…')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByRole('button', { name: 'Revoke' })).toBeInTheDocument()
    expect(screen.queryByText('Loading Faculty assignments…')).not.toBeInTheDocument()
    resolve({ ...assignmentData, assignments: [] })
    expect(await screen.findByText('No active Faculty assignments.')).toBeInTheDocument()
    expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2)
  })

  it('renders the page sections, API-derived counts and distinct active faculty', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({ ...assignmentData, assignments: [
      { ...assignmentData.assignments[0], assignment_id: 'a1' },
      { ...assignmentData.assignments[0], assignment_id: 'a2' },
      { ...assignmentData.assignments[0], assignment_id: 'disabled', is_active: false },
      { ...assignmentData.assignments[0], assignment_id: 'expired', end_at: '2001-01-01T00:00:00Z' },
      { ...assignmentData.assignments[0], assignment_id: 'scheduled', start_at: '2100-01-01T00:00:00Z' },
    ] })
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({ ...responsibilityManagementFixture, responsibilities: [
      ...responsibilityManagementFixture.responsibilities,
      { ...responsibilityManagementFixture.responsibilities[0], responsibility_id: 'other', faculty_user_id: 'other-faculty' },
      { ...responsibilityManagementFixture.responsibilities[0], responsibility_id: 'inactive', state: 'inactive', effective_active: false },
    ] })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    expect(screen.getByRole('heading', { name: 'Faculty Assignments', level: 1 })).toBeInTheDocument()
    for (const title of ['Create Teaching Assignment', 'Current Teaching Assignments', 'Responsibilities & Assignments']) expect(screen.getByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
    expect(within(screen.getByLabelText('Active Assignments')).getByText('2')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Faculty Members')).getByText('1')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Active Responsibilities')).getByText('3')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(6)
    expect(screen.getByText('Showing 5 of 5 assignments')).toBeInTheDocument()
    expect(api.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(1)
  })

  it('shows unavailable counts when validity data is absent rather than inventing active state', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({ ...assignmentData, assignments: [{ ...assignmentData.assignments[0], start_at: undefined }] })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    expect(within(screen.getByLabelText('Active Assignments')).getByText('Unavailable')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Faculty Members')).getByText('Unavailable')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('unavailable')).toBeInTheDocument()
  })

  it('creates the chosen faculty and section using local input converted to UTC', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({ ...assignmentData,
      faculty: [...assignmentData.faculty, { id: 'faculty-2', first_name: 'Grace', last_name: 'Hopper', email: 'grace@example.test' }],
      sections: [...assignmentData.sections, { ...assignmentData.sections[0], section_id: 'section-2', code: 'B' }],
    })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.change(screen.getByLabelText(/Faculty member/), { target: { value: 'faculty-2' } })
    fireEvent.change(screen.getByLabelText(/^Section/), { target: { value: 'section-2' } })
    fireEvent.change(screen.getByLabelText('Teaching start (optional)'), { target: { value: '2026-10-09T09:00' } })
    fireEvent.change(screen.getByLabelText('Teaching end (optional)'), { target: { value: '2026-10-09T10:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    await waitFor(() => expect(api.createFacultyAssignment).toHaveBeenCalledWith('jwt', { faculty_user_id: 'faculty-2', section_id: 'section-2', start_at: new Date('2026-10-09T09:00').toISOString(), end_at: new Date('2026-10-09T10:00').toISOString() }))
    await screen.findByText('Faculty section assignment saved.')
    expect(screen.getByLabelText('Teaching start (optional)')).toHaveValue('')
    expect(screen.getByLabelText(/Faculty member/)).toHaveValue('faculty-2')
  })

  it('clears the form and gives field validation without sending a request', async () => {
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(screen.getByRole('button', { name: 'Clear form' }))
    expect(screen.getByLabelText(/Faculty member/)).toHaveValue('')
    expect(screen.getByLabelText(/^Section/)).toHaveValue('')
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    expect(screen.getByLabelText(/Faculty member/)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Choose a faculty member.')).toBeInTheDocument()
    expect(screen.getByText('Choose an eligible section.')).toBeInTheDocument()
    expect(api.createFacultyAssignment).not.toHaveBeenCalled()
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it.each([
    ['', '2026-10-09T10:00', 'Choose a teaching start'],
    ['2026-10-09T10:00', '2026-10-09T10:00', 'End must be later'],
    ['2026-10-09T10:00', '2026-10-09T09:00', 'End must be later'],
  ])('rejects an unsupported or invalid teaching period %s / %s', async (start, end, message) => {
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.change(screen.getByLabelText('Teaching start (optional)'), { target: { value: start } })
    fireEvent.change(screen.getByLabelText('Teaching end (optional)'), { target: { value: end } })
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.getByLabelText('Teaching end (optional)')).toHaveAccessibleDescription(new RegExp(message))
    expect(api.createFacultyAssignment).not.toHaveBeenCalled()
  })

  it('prevents duplicate creation while a request is pending', async () => {
    let resolve!: (value: { assignment_id: string }) => void
    vi.mocked(api.createFacultyAssignment).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    const button = await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(button)
    expect(button).toBeDisabled()
    fireEvent.submit(button.closest('form')!)
    expect(api.createFacultyAssignment).toHaveBeenCalledTimes(1)
    resolve({ assignment_id: 'assignment-2' })
    await screen.findByText('Faculty section assignment saved.')
  })

  it.each(['Ada', 'faculty@example.test', 'MATH101', 'Section A'])('searches loaded records for %s without another request', async (needle) => {
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    const search = screen.getByRole('searchbox', { name: 'Search teaching assignments' })
    fireEvent.change(search, { target: { value: needle } })
    expect(screen.getByText('Showing 1 of 1 assignments')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'no match' } })
    expect(screen.getByText('No assignments match your search.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 1 assignments')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByText('Showing 1 of 1 assignments')).toBeInTheDocument()
    expect(api.getFacultyAssignments).toHaveBeenCalledTimes(1)
  })

  it('uses the existing teaching editor, validates the period, and refreshes after saving', async () => {
    render(<FacultyAssignmentManager accessToken="jwt" />)
    const table = within(await screen.findByRole('table'))
    fireEvent.click(table.getByRole('button', { name: 'Manage teaching' }))
    fireEvent.change(screen.getByLabelText('Teaching validity start'), { target: { value: '2026-10-09T09:00' } })
    fireEvent.change(screen.getByLabelText('Teaching validity end'), { target: { value: '2026-10-09T08:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save teaching validity' }))
    expect(screen.getByRole('alert')).toHaveTextContent('End must be later')
    expect(api.updateFacultyTeachingValidity).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Teaching validity end'), { target: { value: '2026-10-09T10:00' } })
    fireEvent.click(screen.getByLabelText('Teaching enabled'))
    fireEvent.click(screen.getByRole('button', { name: 'Save teaching validity' }))
    await waitFor(() => expect(api.updateFacultyTeachingValidity).toHaveBeenCalledWith('jwt', 'assignment-1', { start_at: new Date('2026-10-09T09:00').toISOString(), end_at: new Date('2026-10-09T10:00').toISOString(), is_active: false }))
    await waitFor(() => expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('button', { name: 'Save teaching validity' })).not.toBeInTheDocument()
  })

  it('preserves teaching edit entries after failure and supports cancel', async () => {
    vi.mocked(api.updateFacultyTeachingValidity).mockRejectedValueOnce(new Error('Validity overlaps another assignment'))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    fireEvent.click(within(await screen.findByRole('table')).getByRole('button', { name: 'Manage teaching' }))
    fireEvent.change(screen.getByLabelText('Teaching validity start'), { target: { value: '2026-10-09T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save teaching validity' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('overlaps')
    expect(screen.getByLabelText('Teaching validity start')).toHaveValue('2026-10-09T09:00')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel teaching edit' }))
    expect(screen.queryByRole('button', { name: 'Save teaching validity' })).not.toBeInTheDocument()
  })

  it('confirms revocation, respects cancellation, and refreshes after confirmed revoke', async () => {
    render(<FacultyAssignmentManager accessToken="jwt" />)
    const revoke = within(await screen.findByRole('table')).getByRole('button', { name: 'Revoke' })
    vi.mocked(window.confirm).mockReturnValueOnce(false)
    fireEvent.click(revoke)
    expect(api.revokeFacultyAssignment).not.toHaveBeenCalled()
    fireEvent.click(revoke)
    await waitFor(() => expect(api.revokeFacultyAssignment).toHaveBeenCalledWith('jwt', 'assignment-1'))
    expect(window.confirm).toHaveBeenCalledWith('Revoke this Faculty section assignment?')
    expect(await screen.findByRole('status')).toHaveTextContent('revoked')
    await waitFor(() => expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2))
  })

  it('shows a loading state, true zero counts and an empty state without fake assignments', async () => {
    let resolve!: (value: typeof assignmentData) => void
    vi.mocked(api.getFacultyAssignments).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(screen.getByText('Loading Faculty assignments…')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Assign section' })).not.toBeInTheDocument()
    resolve({ ...assignmentData, assignments: [] })
    expect(await screen.findByText('No active Faculty assignments.')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Active Assignments')).getByText('0')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create first assignment' }))
    expect(screen.getByLabelText(/Faculty member/)).toHaveFocus()
  })

  it('disables creation with helpful messages when options are empty', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({ faculty: [], sections: [], assignments: [] })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(await screen.findByRole('button', { name: 'Assign section' })).toBeDisabled()
    expect(screen.getByText(/No eligible sections are available/)).toBeInTheDocument()
    expect(screen.getByText(/No eligible faculty members are available/)).toBeInTheDocument()
    expect(api.createFacultyAssignment).not.toHaveBeenCalled()
  })

  it('preserves entries and last loaded records after a failed refresh, disabling mutations until retry', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValueOnce(assignmentData).mockRejectedValueOnce(Object.assign(new Error('raw server diagnostics'), { status: 500 }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.change(screen.getByLabelText('Teaching start (optional)'), { target: { value: '2026-10-09T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh assignments' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('server could not complete')
    expect(screen.queryByText('raw server diagnostics')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Teaching start (optional)')).toHaveValue('2026-10-09T09:00')
    expect(within(screen.getByRole('table')).getByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Assign section' })).toBeDisabled()
    expect(within(screen.getByRole('table')).getByRole('button', { name: 'Manage teaching' })).toBeDisabled()
    expect(within(screen.getByLabelText('Active Assignments')).getByText('Unavailable')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading assignments' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Assign section' })).toBeEnabled())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('distinguishes permission denial and offers no mutation controls when data is denied', async () => {
    vi.mocked(api.getFacultyAssignments).mockRejectedValueOnce(Object.assign(new Error('HTTP 403'), { status: 403 }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('do not have permission')
    expect(screen.queryByRole('button', { name: 'Assign section' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Manage teaching' })).not.toBeInTheDocument()
    expect(api.createFacultyAssignment).not.toHaveBeenCalled()
  })

  it('shows unavailable responsibility counts and a retry while teaching data remains usable', async () => {
    vi.mocked(api.getFacultyResponsibilityManagement).mockRejectedValueOnce(Object.assign(new Error('missing responsibility schema'), { status: 503, code: 'FACULTY_SCHEMA_UNAVAILABLE' }))
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database update')
    expect(within(screen.getByLabelText('Active Responsibilities')).getByText('Unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Assign section' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading responsibilities' }))
    await waitFor(() => expect(within(screen.getByLabelText('Active Responsibilities')).getByText('0')).toBeInTheDocument())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

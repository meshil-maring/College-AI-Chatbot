import './__tests__/FacultyAssignmentManager.support.tsx'
import { assignmentData } from './__tests__/FacultyAssignmentManager.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import FacultyAssignmentManager from './FacultyAssignmentManager.tsx'
describe('FacultyAssignmentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.getFacultyAssignments).mockResolvedValue(assignmentData)
    vi.mocked(api.createFacultyAssignment).mockResolvedValue({ assignment_id: 'assignment-2' })
    vi.mocked(api.revokeFacultyAssignment).mockResolvedValue({ assignment_id: 'assignment-1' })
    vi.mocked(api.updateFacultyTeachingValidity).mockResolvedValue({ assignment_id: 'assignment-1' })
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({
      faculty: assignmentData.faculty,
      definitions: [],
      departments: [],
      sections: [],
      responsibilities: [],
    })
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
    await waitFor(() =>
      expect(api.updateFacultyTeachingValidity).toHaveBeenCalledWith('jwt', 'assignment-1', {
        start_at: new Date('2026-10-09T09:00').toISOString(),
        end_at: new Date('2026-10-09T10:00').toISOString(),
        is_active: false,
      }),
    )
    await waitFor(() => expect(api.getFacultyAssignments).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('button', { name: 'Save teaching validity' })).not.toBeInTheDocument()
  })

  it('preserves teaching edit entries after failure and supports cancel', async () => {
    vi.mocked(api.updateFacultyTeachingValidity).mockRejectedValueOnce(
      new Error('Validity overlaps another assignment'),
    )
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
    vi.mocked(api.getFacultyAssignments).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
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
    vi.mocked(api.getFacultyAssignments)
      .mockResolvedValueOnce(assignmentData)
      .mockRejectedValueOnce(Object.assign(new Error('raw server diagnostics'), { status: 500 }))
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
    vi.mocked(api.getFacultyResponsibilityManagement).mockRejectedValueOnce(
      Object.assign(new Error('missing responsibility schema'), { status: 503, code: 'FACULTY_SCHEMA_UNAVAILABLE' }),
    )
    render(<FacultyAssignmentManager accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database update')
    expect(within(screen.getByLabelText('Active Responsibilities')).getByText('Unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Assign section' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading responsibilities' }))
    await waitFor(() =>
      expect(within(screen.getByLabelText('Active Responsibilities')).getByText('0')).toBeInTheDocument(),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

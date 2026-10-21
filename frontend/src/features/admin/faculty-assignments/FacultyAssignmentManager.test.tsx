import './__tests__/FacultyAssignmentManager.support.tsx'
import { assignmentData } from './__tests__/FacultyAssignmentManager.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import { responsibilityManagementFixture } from '../../../test/facultyResponsibilitiesFixtures.ts'
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
    vi.mocked(api.getFacultyAssignments).mockRejectedValueOnce(
      new Error(
        'Faculty assignments and responsibilities are unavailable until the database update is applied. Please contact your administrator.',
      ),
    )
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
    vi.mocked(api.getFacultyAssignments)
      .mockResolvedValueOnce(assignmentData)
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            resolve = done
          }),
      )
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
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({
      ...assignmentData,
      assignments: [
        { ...assignmentData.assignments[0], assignment_id: 'a1' },
        { ...assignmentData.assignments[0], assignment_id: 'a2' },
        { ...assignmentData.assignments[0], assignment_id: 'disabled', is_active: false },
        { ...assignmentData.assignments[0], assignment_id: 'expired', end_at: '2001-01-01T00:00:00Z' },
        { ...assignmentData.assignments[0], assignment_id: 'scheduled', start_at: '2100-01-01T00:00:00Z' },
      ],
    })
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({
      ...responsibilityManagementFixture,
      responsibilities: [
        ...responsibilityManagementFixture.responsibilities,
        {
          ...responsibilityManagementFixture.responsibilities[0],
          responsibility_id: 'other',
          faculty_user_id: 'other-faculty',
        },
        {
          ...responsibilityManagementFixture.responsibilities[0],
          responsibility_id: 'inactive',
          state: 'inactive',
          effective_active: false,
        },
      ],
    })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    expect(screen.getByRole('heading', { name: 'Faculty Assignments', level: 1 })).toBeInTheDocument()
    for (const title of [
      'Create Teaching Assignment',
      'Current Teaching Assignments',
      'Responsibilities & Assignments',
    ])
      expect(screen.getByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
    expect(within(screen.getByLabelText('Active Assignments')).getByText('2')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Faculty Members')).getByText('1')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Active Responsibilities')).getByText('3')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(6)
    expect(screen.getByText('Showing 5 of 5 assignments')).toBeInTheDocument()
    expect(api.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(1)
  })

  it('shows unavailable counts when validity data is absent rather than inventing active state', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({
      ...assignmentData,
      assignments: [{ ...assignmentData.assignments[0], start_at: undefined }],
    })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    expect(within(screen.getByLabelText('Active Assignments')).getByText('Unavailable')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Faculty Members')).getByText('Unavailable')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('unavailable')).toBeInTheDocument()
  })

  it('creates the chosen faculty and section using local input converted to UTC', async () => {
    vi.mocked(api.getFacultyAssignments).mockResolvedValue({
      ...assignmentData,
      faculty: [
        ...assignmentData.faculty,
        { id: 'faculty-2', first_name: 'Grace', last_name: 'Hopper', email: 'grace@example.test' },
      ],
      sections: [...assignmentData.sections, { ...assignmentData.sections[0], section_id: 'section-2', code: 'B' }],
    })
    render(<FacultyAssignmentManager accessToken="jwt" />)
    await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.change(screen.getByLabelText(/Faculty member/), { target: { value: 'faculty-2' } })
    fireEvent.change(screen.getByLabelText(/^Section/), { target: { value: 'section-2' } })
    fireEvent.change(screen.getByLabelText('Teaching start (optional)'), { target: { value: '2026-10-09T09:00' } })
    fireEvent.change(screen.getByLabelText('Teaching end (optional)'), { target: { value: '2026-10-09T10:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Assign section' }))
    await waitFor(() =>
      expect(api.createFacultyAssignment).toHaveBeenCalledWith('jwt', {
        faculty_user_id: 'faculty-2',
        section_id: 'section-2',
        start_at: new Date('2026-10-09T09:00').toISOString(),
        end_at: new Date('2026-10-09T10:00').toISOString(),
      }),
    )
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
    vi.mocked(api.createFacultyAssignment).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    render(<FacultyAssignmentManager accessToken="jwt" />)
    const button = await screen.findByRole('button', { name: 'Assign section' })
    fireEvent.click(button)
    expect(button).toBeDisabled()
    fireEvent.submit(button.closest('form')!)
    expect(api.createFacultyAssignment).toHaveBeenCalledTimes(1)
    resolve({ assignment_id: 'assignment-2' })
    await screen.findByText('Faculty section assignment saved.')
  })

  it.each(['Ada', 'faculty@example.test', 'MATH101', 'Section A'])(
    'searches loaded records for %s without another request',
    async (needle) => {
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
    },
  )
})

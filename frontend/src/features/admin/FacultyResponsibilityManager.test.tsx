import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyResponsibilityManager from './FacultyResponsibilityManager.tsx'
import * as api from '../../services/adminApi.ts'
import { responsibilityManagementFixture } from '../../test/facultyResponsibilitiesFixtures.ts'

vi.mock('../../services/adminApi.ts')
beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue(responsibilityManagementFixture)
  vi.mocked(api.createFacultyResponsibility).mockResolvedValue({ responsibility_id: 'new-1' })
  vi.mocked(api.updateFacultyResponsibility).mockResolvedValue({ responsibility_id: 'hod-1' })
  vi.mocked(api.revokeFacultyResponsibility).mockResolvedValue({ responsibility_id: 'hod-1' })
})

describe('Faculty responsibility management', () => {
  it('displays separate positions with authoritative scope and validity', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    const records = within(await screen.findByRole('complementary', { name: 'Current Responsibilities' }))
    expect(await records.findByText('HOD')).toBeInTheDocument()
    expect(records.getByText('CSE Department')).toBeInTheDocument()
    expect(records.getByText('Class In-Charge')).toBeInTheDocument()
    expect(records.getByText('B.Tech CSE · Semester 5 · Section A')).toBeInTheDocument()
    expect(screen.getAllByText(/No end date/)).toHaveLength(2)
  })

  it('creates a responsibility with validity and sends no tenant, actor, or permissions', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    await screen.findByRole('button', { name: 'Add responsibility' })
    fireEvent.click(screen.getByRole('button', { name: 'Add responsibility' }))
    await waitFor(() => expect(api.createFacultyResponsibility).toHaveBeenCalledWith('jwt', {
      faculty_user_id: 'faculty-1', responsibility_code: 'hod', scope_type: 'department', scope_id: 'department-1',
      start_at: expect.any(String), end_at: null, is_active: true,
    }))
    expect(await screen.findByRole('status')).toHaveTextContent('Responsibility added.')
  })

  it('updates validity and enabled state using the existing appointment', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Manage HOD' }))
    fireEvent.click(screen.getByLabelText('Appointment enabled'))
    fireEvent.click(screen.getByRole('button', { name: 'Save responsibility' }))
    await waitFor(() => expect(api.updateFacultyResponsibility).toHaveBeenCalledWith('jwt', 'hod-1', expect.objectContaining({ scope_id: 'department-1', is_active: false })))
  })

  it('revokes and refreshes without erasing history', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Revoke HOD' }))
    await waitFor(() => expect(api.revokeFacultyResponsibility).toHaveBeenCalledWith('jwt', 'hod-1'))
    expect(await screen.findByRole('status')).toHaveTextContent('Responsibility revoked.')
    expect(api.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(2)
  })

  it('shows conflict or 403 failures without reporting success', async () => {
    vi.mocked(api.createFacultyResponsibility).mockRejectedValue(new Error('This responsibility overlaps an existing appointment'))
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add responsibility' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('overlaps')
    expect(screen.queryByText('Responsibility added.')).not.toBeInTheDocument()
  })

  it('creates an API-defined class responsibility in its selected scope with local validity', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    await screen.findByRole('button', { name: 'Add responsibility' })
    fireEvent.change(screen.getByRole('combobox', { name: 'Responsibility' }), { target: { value: 'class_in_charge' } })
    expect(screen.getByLabelText(/Responsibility scope/)).toHaveValue('section-1')
    fireEvent.change(screen.getByLabelText(/Responsibility start/), { target: { value: '2026-10-09T09:00' } })
    fireEvent.change(screen.getByLabelText(/Responsibility end/), { target: { value: '2026-10-09T10:00' } })
    fireEvent.click(screen.getByLabelText('Appointment enabled'))
    fireEvent.click(screen.getByRole('button', { name: 'Add responsibility' }))
    await waitFor(() => expect(api.createFacultyResponsibility).toHaveBeenCalledWith('jwt', { faculty_user_id: 'faculty-1', responsibility_code: 'class_in_charge', scope_type: 'section', scope_id: 'section-1', start_at: new Date('2026-10-09T09:00').toISOString(), end_at: new Date('2026-10-09T10:00').toISOString(), is_active: false }))
  })

  it('validates required start and exclusive end beside the fields without sending requests', async () => {
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    await screen.findByRole('button', { name: 'Add responsibility' })
    fireEvent.change(screen.getByLabelText(/Responsibility start/), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add responsibility' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a start')
    expect(screen.getByLabelText(/Responsibility start/)).toHaveAttribute('aria-invalid', 'true')
    fireEvent.change(screen.getByLabelText(/Responsibility start/), { target: { value: '2026-10-09T09:00' } })
    fireEvent.change(screen.getByLabelText(/Responsibility end/), { target: { value: '2026-10-09T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add responsibility' }))
    expect(screen.getByRole('alert')).toHaveTextContent('End must be later')
    expect(api.createFacultyResponsibility).not.toHaveBeenCalled()
  })

  it('preserves form entries after HTTP 500, hides diagnostics and prevents fake success', async () => {
    vi.mocked(api.createFacultyResponsibility).mockRejectedValueOnce(Object.assign(new Error('raw database trace'), { status: 500 }))
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    await screen.findByRole('button', { name: 'Add responsibility' })
    fireEvent.change(screen.getByLabelText(/Responsibility start/), { target: { value: '2026-10-09T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add responsibility' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('server could not complete')
    expect(screen.getByLabelText(/Responsibility start/)).toHaveValue('2026-10-09T09:00')
    expect(screen.queryByText('raw database trace')).not.toBeInTheDocument()
    expect(screen.queryByText('Responsibility added.')).not.toBeInTheDocument()
  })

  it('does not duplicate responsibility creation while saving', async () => {
    let resolve!: (value: { responsibility_id: string }) => void
    vi.mocked(api.createFacultyResponsibility).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    const button = await screen.findByRole('button', { name: 'Add responsibility' })
    fireEvent.click(button)
    expect(button).toBeDisabled()
    fireEvent.submit(button.closest('form')!)
    expect(api.createFacultyResponsibility).toHaveBeenCalledTimes(1)
    resolve({ responsibility_id: 'new-1' })
    expect(await screen.findByRole('status')).toHaveTextContent('Responsibility added.')
  })

  it('shows schema unavailability rather than an empty list and recovers on retry', async () => {
    vi.mocked(api.getFacultyResponsibilityManagement).mockRejectedValueOnce(Object.assign(new Error('internal schema cache error'), { status: 503, code: 'FACULTY_SCHEMA_UNAVAILABLE' }))
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database update')
    expect(screen.queryByText('No responsibilities for the selected Faculty member.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add responsibility' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading responsibilities' }))
    expect(await screen.findByRole('button', { name: 'Add responsibility' })).toBeEnabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(2)
  })

  it('keeps records and form entries visible after refresh denial and disables management', async () => {
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValueOnce(responsibilityManagementFixture).mockRejectedValueOnce(Object.assign(new Error('Permission denied'), { status: 403 }))
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add responsibility' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('do not have permission')
    expect(screen.getByRole('button', { name: 'Manage HOD' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Revoke HOD' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add responsibility' })).toBeDisabled()
    expect(within(screen.getByRole('complementary')).getByText('CSE Department')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading responsibilities' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Manage HOD' })).toBeEnabled())
  })

  it('renders true empty records and disables creation for missing faculty or scopes', async () => {
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({ ...responsibilityManagementFixture, departments: [], responsibilities: [] })
    const { rerender } = render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    expect(await screen.findByText('No responsibilities for the selected Faculty member.')).toBeInTheDocument()
    expect(screen.getByText('No eligible scopes are available for this responsibility.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add responsibility' })).toBeDisabled()
    rerender(<FacultyResponsibilityManager accessToken="jwt" facultyId="" />)
    expect(screen.getByRole('button', { name: 'Add responsibility' })).toBeDisabled()
    expect(api.createFacultyResponsibility).not.toHaveBeenCalled()
  })

  it('resets editing when switching faculty so an appointment cannot be saved under another selection', async () => {
    const { rerender } = render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Manage HOD' }))
    expect(screen.getByRole('button', { name: 'Save responsibility' })).toBeInTheDocument()
    rerender(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-2" />)
    expect(screen.queryByRole('button', { name: 'Save responsibility' })).not.toBeInTheDocument()
    expect(screen.getByText('No responsibilities for the selected Faculty member.')).toBeInTheDocument()
    expect(api.updateFacultyResponsibility).not.toHaveBeenCalled()
  })

  it('uses authoritative revoked state and hides actions while preserving appointment history', async () => {
    vi.mocked(api.getFacultyResponsibilityManagement).mockResolvedValue({ ...responsibilityManagementFixture, responsibilities: [{ ...responsibilityManagementFixture.responsibilities[0], revoked_at: '2026-10-08T00:00:00Z', state: 'revoked', effective_active: false }] })
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    expect(await screen.findByText('revoked')).toBeInTheDocument()
    expect(within(screen.getByRole('complementary')).getByText('CSE Department')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Manage HOD' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Revoke HOD' })).not.toBeInTheDocument()
  })

  it('respects revocation cancellation', async () => {
    vi.mocked(window.confirm).mockReturnValueOnce(false)
    render(<FacultyResponsibilityManager accessToken="jwt" facultyId="faculty-1" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Revoke HOD' }))
    expect(api.revokeFacultyResponsibility).not.toHaveBeenCalled()
  })
})

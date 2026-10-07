import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    expect(await screen.findByText('HOD — CSE Department')).toBeInTheDocument()
    expect(screen.getByText('Class In-Charge — B.Tech CSE · Semester 5 · Section A')).toBeInTheDocument()
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
})

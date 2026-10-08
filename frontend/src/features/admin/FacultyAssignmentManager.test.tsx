import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyAssignmentManager from './FacultyAssignmentManager.tsx'
import * as api from '../../services/adminApi.ts'

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
    faculty: { email: 'faculty@example.test', first_name: 'Ada', last_name: 'Lovelace' },
    section: { name: 'Section A', code: 'A', course: { name: 'Mathematics', code: 'MATH101' } },
  }],
}

describe('FacultyAssignmentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.getFacultyAssignments).mockResolvedValue(assignmentData)
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
})

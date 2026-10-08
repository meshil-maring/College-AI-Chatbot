import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ScopedTeachingAssignmentManager from './ScopedTeachingAssignmentManager.tsx'
import * as api from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')

const data = {
  sections: [{
    section_id: 'section-cse-5a',
    name: 'Section A',
    code: 'A',
    course: { name: 'Database Systems', code: 'CS501' },
    program: { name: 'CSE' },
    semester: { name: 'Semester 5' },
    academic_year: { name: '2026-27' },
  }],
  faculty: [{
    id: 'faculty-2',
    email: 'faculty@example.test',
    first_name: 'Grace',
    last_name: 'Hopper',
  }],
  assignments: [],
}

describe('ScopedTeachingAssignmentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getScopedTeachingAssignments).mockResolvedValue(data)
    vi.mocked(api.createScopedTeachingAssignment).mockResolvedValue({ assignment_id: 'assignment-1' })
  })

  it('creates an assignment using the chosen scoped faculty, section, and validity', async () => {
    render(<ScopedTeachingAssignmentManager accessToken="jwt" />)
    const faculty = await screen.findByLabelText('Faculty member')
    const section = screen.getByLabelText('Course / section')
    fireEvent.change(faculty, { target: { value: 'faculty-2' } })
    fireEvent.change(section, { target: { value: 'section-cse-5a' } })
    fireEvent.change(screen.getByLabelText('Valid from'), { target: { value: '2026-10-07T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create assignment' }))

    await waitFor(() => {
      expect(api.createScopedTeachingAssignment).toHaveBeenCalledWith('jwt', {
        faculty_user_id: 'faculty-2',
        section_id: 'section-cse-5a',
        start_at: new Date('2026-10-07T09:00').toISOString(),
        end_at: null,
        is_active: true,
      })
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Teaching assignment created.')
  })

  it('rejects invalid validity intervals before sending a mutation', async () => {
    render(<ScopedTeachingAssignmentManager accessToken="jwt" />)
    fireEvent.change(await screen.findByLabelText('Faculty member'), { target: { value: 'faculty-2' } })
    fireEvent.change(screen.getByLabelText('Course / section'), { target: { value: 'section-cse-5a' } })
    fireEvent.change(screen.getByLabelText('Valid from'), { target: { value: '2026-10-08T09:00' } })
    fireEvent.change(screen.getByLabelText('Valid until (optional)'), { target: { value: '2026-10-07T09:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create assignment' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('must be later')
    expect(api.createScopedTeachingAssignment).not.toHaveBeenCalled()
  })
})

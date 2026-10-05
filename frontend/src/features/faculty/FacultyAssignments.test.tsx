import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyAssignments from './FacultyAssignments.tsx'
import * as api from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')

describe('FacultyAssignments', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders only the active assignment projection supplied by the server', async () => {
    vi.mocked(api.getMyFacultyAssignments).mockResolvedValue([{
      assignment_id: 'assignment-1',
      assigned_at: '2026-10-05T00:00:00Z',
      section: {
        section_id: 'section-1',
        name: 'Section A',
        code: 'A',
        course: { name: 'Mathematics', code: 'MATH101' },
      },
    }])
    render(<FacultyAssignments accessToken="jwt" />)
    expect(await screen.findByText('MATH101 · A')).toBeInTheDocument()
    expect(screen.getByText('Mathematics — Section A')).toBeInTheDocument()
    expect(api.getMyFacultyAssignments).toHaveBeenCalledWith('jwt')
  })

  it('shows backend failures explicitly', async () => {
    vi.mocked(api.getMyFacultyAssignments).mockRejectedValue(new Error('Session expired'))
    render(<FacultyAssignments accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Session expired')
  })
})

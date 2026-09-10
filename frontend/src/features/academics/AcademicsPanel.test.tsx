/**
 * Phase Admin-4 — AcademicsPanel component tests.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AcademicsPanel from './AcademicsPanel.tsx'
import * as adminApi from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'test-token', user: null, logout: vi.fn() }),
}))

describe('AcademicsPanel', () => {
  it('shows My Academics button when closed', () => {
    render(<AcademicsPanel />)
    expect(screen.getByText('My Academics')).toBeInTheDocument()
  })

  it('opens the panel when button is clicked', async () => {
    const user = userEvent.setup()
    render(<AcademicsPanel />)
    await user.click(screen.getByText('My Academics'))
    expect(screen.getByText('My Academics')).toBeInTheDocument()
    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('Results')).toBeInTheDocument()
    expect(screen.getByText('Test Results')).toBeInTheDocument()
    expect(screen.getByText('Attendance')).toBeInTheDocument()
  })

  it('loads and displays profile data', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.getMyProfile).mockResolvedValue({
      student_id: 's1',
      user_id: 'u1',
      institution_id: 'i1',
      student_number: 'S100',
      program_id: null,
      academic_year_id: null,
      enrollment_date: '2025-08-01',
      expected_graduation_date: null,
      status: 'active',
      is_active: true,
      created_at: '2025-08-01T00:00:00Z',
      updated_at: '2025-08-01T00:00:00Z',
    })
    vi.mocked(adminApi.getMyResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyTestResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyAttendance).mockResolvedValue([])

    render(<AcademicsPanel />)
    await user.click(screen.getByText('My Academics'))
    await waitFor(() => {
      expect(screen.getByText('S100')).toBeInTheDocument()
    })
  })

  it('shows error state when profile fetch fails', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.getMyProfile).mockRejectedValue(new Error('Not found'))
    vi.mocked(adminApi.getMyResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyTestResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyAttendance).mockResolvedValue([])

    render(<AcademicsPanel />)
    await user.click(screen.getByText('My Academics'))
    await waitFor(() => {
      expect(screen.getByText('Not found')).toBeInTheDocument()
    })
  })

  it('shows empty state for results when none available', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.getMyProfile).mockResolvedValue({
      student_id: 's1',
      user_id: 'u1',
      institution_id: 'i1',
      student_number: 'S100',
      program_id: null,
      academic_year_id: null,
      enrollment_date: null,
      expected_graduation_date: null,
      status: 'active',
      is_active: true,
      created_at: '2025-08-01T00:00:00Z',
      updated_at: '2025-08-01T00:00:00Z',
    })
    vi.mocked(adminApi.getMyResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyTestResults).mockResolvedValue([])
    vi.mocked(adminApi.getMyAttendance).mockResolvedValue([])

    render(<AcademicsPanel />)
    await user.click(screen.getByText('My Academics'))
    await user.click(screen.getByText('Results'))
    await waitFor(() => {
      expect(screen.getByText('No results available.')).toBeInTheDocument()
    })
  })
})

/**
 * Phase 6.19 — AdminApprovals tests.
 *
 * The admin view of the Phase 6.4 approval-queue contract. Pins: loading /
 * empty / error / retry states, safe fields only (no internal identifiers),
 * approve/reject call the shared client, and a 409 STUDENT_NOT_PENDING
 * refreshes the queue instead of faking success.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminApprovals from './AdminApprovals.tsx'
import type { PendingStudent } from '../../types/admin.ts'

const adminApi = vi.hoisted(() => ({
  AdminApiError: class AdminApiError extends Error {
    readonly status: number
    constructor(status: number, message: string) {
      super(message)
      this.name = 'AdminApiError'
      this.status = status
    }
  },
  listPendingStudents: vi.fn(),
  approvePendingStudent: vi.fn(),
  rejectPendingStudent: vi.fn(),
}))

vi.mock('../../services/adminApi.ts', () => adminApi)

const PENDING: PendingStudent = {
  student_id: 's-1',
  user_id: 'u-1',
  institution_id: 'inst-1',
  student_number: 'STU-0001',
  email: 'student@test.com',
  register_number: 'REG-001',
  university_roll_number: null,
  approval_status: 'pending',
  status: 'active',
  is_active: true,
  enrollment_date: null,
  created_at: '',
  updated_at: '',
}

beforeEach(() => {
  adminApi.listPendingStudents.mockReset()
  adminApi.approvePendingStudent.mockReset()
  adminApi.rejectPendingStudent.mockReset()
})

describe('AdminApprovals', () => {
  it('shows a loading status while the queue request is in flight', () => {
    vi.mocked(adminApi.listPendingStudents).mockReturnValue(new Promise(() => {}))
    render(<AdminApprovals accessToken="token" />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading pending registrations…')
  })

  it('shows an empty status when nobody is pending', async () => {
    vi.mocked(adminApi.listPendingStudents).mockResolvedValue([])
    render(<AdminApprovals accessToken="token" />)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('No students are awaiting approval')
    })
  })

  it('renders safe decision fields only — never internal identifiers', async () => {
    vi.mocked(adminApi.listPendingStudents).mockResolvedValue([PENDING])
    render(<AdminApprovals accessToken="token" />)
    await waitFor(() => {
      expect(screen.getByText('STU-0001')).toBeInTheDocument()
    })
    expect(screen.getByText('student@test.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument()
    // Data minimization: internal identifiers are never rendered.
    expect(screen.queryByText('s-1')).not.toBeInTheDocument()
    expect(screen.queryByText('u-1')).not.toBeInTheDocument()
    expect(screen.queryByText('inst-1')).not.toBeInTheDocument()
  })

  it('approves a pending student and removes the row', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listPendingStudents).mockResolvedValue([PENDING])
    vi.mocked(adminApi.approvePendingStudent).mockResolvedValue({
      ...PENDING,
      approval_status: 'approved',
    })
    render(<AdminApprovals accessToken="token" />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() => {
      expect(adminApi.approvePendingStudent).toHaveBeenCalledWith('token', 's-1')
    })
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('No students are awaiting approval')
    })
  })

  it('refreshes the queue on a 409 conflict instead of faking success', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listPendingStudents)
      .mockResolvedValueOnce([PENDING])
      .mockResolvedValueOnce([]) // refreshed queue after the conflict
    vi.mocked(adminApi.approvePendingStudent).mockRejectedValue(
      new adminApi.AdminApiError(409, 'Student is not pending approval'),
    )
    render(<AdminApprovals accessToken="token" />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() => {
      expect(screen.getByText(/already processed/i)).toBeInTheDocument()
    })
    expect(vi.mocked(adminApi.listPendingStudents)).toHaveBeenCalledTimes(2)
  })

  it('surfaces a load error with retry', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listPendingStudents)
      .mockRejectedValueOnce(new adminApi.AdminApiError(500, 'Server error'))
      .mockResolvedValueOnce([])
    render(<AdminApprovals accessToken="token" />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server error')
    })
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('No students are awaiting approval')
    })
  })
})
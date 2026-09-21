/**
 * Phase 6.18 — Staff approval queue tests.
 *
 * Covers the ONLY operational data view of the staff shell: loading /
 * empty / error / retry states, approve + reject flows, the 409
 * already-processed recovery path, and data minimization (no internal IDs
 * rendered).
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StaffApprovals from './StaffApprovals.tsx'
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
  student_id: '30000000-0000-0000-0000-000000000301',
  user_id: '30000000-0000-0000-0000-000000000401',
  institution_id: '30000000-0000-0000-0000-000000000001',
  student_number: 'STU-0001',
  email: 'student@college.edu',
  register_number: 'REG-001',
  university_roll_number: null,
  approval_status: 'pending',
  status: 'active',
  is_active: true,
  enrollment_date: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function dictApproval(status: string): PendingStudent {
  return { ...PENDING, approval_status: status }
}

beforeEach(() => {
  adminApi.listPendingStudents.mockReset()
  adminApi.approvePendingStudent.mockReset()
  adminApi.rejectPendingStudent.mockReset()
  adminApi.listPendingStudents.mockResolvedValue([PENDING])
})

describe('StaffApprovals queue states', () => {
  it('shows a loading state while the queue request is in flight', async () => {
    let resolveList: (value: PendingStudent[]) => void = () => {}
    adminApi.listPendingStudents.mockReturnValue(
      new Promise<PendingStudent[]>((resolve) => {
        resolveList = resolve
      }),
    )
    render(<StaffApprovals accessToken="test-token" />)
    expect(screen.getByText('Loading pending registrations…')).toBeInTheDocument()
    resolveList([PENDING])
    await waitFor(() => {
      expect(screen.getByText('STU-0001')).toBeInTheDocument()
    })
  })

  it('renders pending students with safe fields only', async () => {
    render(<StaffApprovals accessToken="test-token" />)
    expect(await screen.findByText('STU-0001')).toBeInTheDocument()
    expect(screen.getByText('student@college.edu')).toBeInTheDocument()
    expect(screen.getByText('REG-001')).toBeInTheDocument()
    // Data minimization: internal identifiers are NEVER rendered.
    expect(screen.queryByText(PENDING.student_id)).not.toBeInTheDocument()
    expect(screen.queryByText(PENDING.user_id)).not.toBeInTheDocument()
    expect(screen.queryByText(PENDING.institution_id)).not.toBeInTheDocument()
  })

  it('shows an empty state when no students are pending', async () => {
    adminApi.listPendingStudents.mockResolvedValue([])
    render(<StaffApprovals accessToken="test-token" />)
    expect(
      await screen.findByText('No students are awaiting approval right now.'),
    ).toBeInTheDocument()
  })

  it('shows an error state with retry and recovers', async () => {
    adminApi.listPendingStudents.mockRejectedValue(
      new adminApi.AdminApiError(500, 'Request failed'),
    )
    render(<StaffApprovals accessToken="test-token" />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    adminApi.listPendingStudents.mockResolvedValue([PENDING])
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('STU-0001')).toBeInTheDocument()
  })
})

describe('StaffApprovals decisions', () => {
  it('approves a student and removes the row from the queue', async () => {
    const user = userEvent.setup()
    adminApi.approvePendingStudent.mockResolvedValue(dictApproval('approved'))
    render(<StaffApprovals accessToken="test-token" />)
    await screen.findByText('STU-0001')
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    expect(adminApi.approvePendingStudent).toHaveBeenCalledWith('test-token', PENDING.student_id)
    await waitFor(() => {
      expect(
        screen.getByText('No students are awaiting approval right now.'),
      ).toBeInTheDocument()
    })
  })

  it('rejects a student and removes the row from the queue', async () => {
    const user = userEvent.setup()
    adminApi.rejectPendingStudent.mockResolvedValue(dictApproval('rejected'))
    render(<StaffApprovals accessToken="test-token" />)
    await screen.findByText('STU-0001')
    await user.click(screen.getByRole('button', { name: 'Reject' }))
    expect(adminApi.rejectPendingStudent).toHaveBeenCalledWith('test-token', PENDING.student_id)
    await waitFor(() => {
      expect(
        screen.getByText('No students are awaiting approval right now.'),
      ).toBeInTheDocument()
    })
  })

  it('refreshes the queue when another approver already decided (409)', async () => {
    const user = userEvent.setup()
    adminApi.approvePendingStudent.mockRejectedValue(
      new adminApi.AdminApiError(409, 'Student is not pending approval'),
    )
    render(<StaffApprovals accessToken="test-token" />)
    await screen.findByText('STU-0001')
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    expect(
      await screen.findByText('This student was already processed. The queue has been refreshed.'),
    ).toBeInTheDocument()
    // The refresh re-lists the queue (initial load + refresh = 2 calls).
    await waitFor(() => {
      expect(adminApi.listPendingStudents).toHaveBeenCalledTimes(2)
    })
  })

  it('surfaces a decision failure without clearing the queue', async () => {
    const user = userEvent.setup()
    adminApi.rejectPendingStudent.mockRejectedValue(
      new adminApi.AdminApiError(500, 'Request failed (FORBIDDEN)'),
    )
    render(<StaffApprovals accessToken="test-token" />)
    await screen.findByText('STU-0001')
    await user.click(screen.getByRole('button', { name: 'Reject' }))
    expect(await screen.findByText('Request failed (FORBIDDEN)')).toBeInTheDocument()
    expect(screen.getByText('STU-0001')).toBeInTheDocument()
  })
})



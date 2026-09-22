/**
 * Phase 6.19 — AdminDashboard tests.
 *
 * The dashboard renders ONLY values supplied by the real authorized contract
 * (GET /admin/dashboard via getDashboardSummary): loading/empty/error/retry
 * states, exactly one request per load, and no fabricated values.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminDashboard from './AdminDashboard.tsx'
import * as adminApi from '../../services/adminApi.ts'
import type { DashboardSummary } from '../../types/admin.ts'

vi.mock('../../services/adminApi.ts')
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    accessToken: 'test-token',
    user: null,
    role: 'admin',
    logout: vi.fn(),
  }),
}))

const SUMMARY: DashboardSummary = {
  counts: {
    knowledge_sources: 2,
    documents: 5,
    faqs: 3,
    notices: 4,
    students: 7,
    student_results: 9,
    test_results: 6,
    attendance_records: 11,
  },
  recent_audit: [
    {
      audit_id: 'aud-1',
      actor_user_id: 'u1',
      action: 'student.approve',
      performed_at: '2026-01-01T00:00:00Z',
      table_name: 'students',
      record_id: null,
      record_data: null,
      ip_address: null,
      user_agent: null,
      status: 'success',
    },
  ],
}

beforeEach(() => {
  vi.mocked(adminApi.getDashboardSummary).mockReset()
})

describe('AdminDashboard', () => {
  it('shows a loading status while the summary request is in flight', () => {
    vi.mocked(adminApi.getDashboardSummary).mockReturnValue(new Promise(() => {}))
    render(<AdminDashboard />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading dashboard…')
  })

  it('renders real counts and audit activity from the contract', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByText('7')).toBeInTheDocument()
    })
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('student.approve')).toBeInTheDocument()
    // No fabricated sections: no invented pending-approvals or activity counts.
    expect(screen.queryByText('Pending approvals')).not.toBeInTheDocument()
  })

  it('shows an empty state when there is no audit activity', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue({ ...SUMMARY, recent_audit: [] })
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByText('No recent activity.')).toBeInTheDocument()
    })
  })

  it('shows an error with retry and requests the summary exactly once per load', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockRejectedValue(new Error('Server error'))
    const user = userEvent.setup()
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server error')
    })
    expect(vi.mocked(adminApi.getDashboardSummary)).toHaveBeenCalledTimes(1)
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument()
    })
    expect(vi.mocked(adminApi.getDashboardSummary)).toHaveBeenCalledTimes(2)
  })
})
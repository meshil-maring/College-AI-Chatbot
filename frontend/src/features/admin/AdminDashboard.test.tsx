/**
 * Phase 7.21 — AdminDashboard tests.
 *
 * The dashboard renders ONLY values supplied by the real authorized contract
 * (GET /admin/dashboard via getDashboardSummary): loading / zero-data / error /
 * retry states, exactly one request per load, metric rendering, quick-action
 * navigation, and the absence of any sensitive or cross-tenant field.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminDashboard from './AdminDashboard.tsx'
import * as adminApi from '../../services/adminApi.ts'
import {
  buildDashboardSummary,
  emptyDashboardSummary,
} from '../../test/adminDashboardFixtures.ts'
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

const SUMMARY: DashboardSummary = buildDashboardSummary()

beforeEach(() => {
  vi.mocked(adminApi.getDashboardSummary).mockReset()
})

describe('AdminDashboard', () => {
  it('shows a loading status while the summary request is in flight', () => {
    vi.mocked(adminApi.getDashboardSummary).mockReturnValue(new Promise(() => {}))
    render(<AdminDashboard />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading dashboard…')
  })

  it('renders the institution overview from the contract', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Institution overview' })).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: 'Alpha University' })).toBeInTheDocument()
    expect(screen.getByText('ALPHA')).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
  })

  it('renders real metrics across every dashboard section', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Key metrics' })).toBeInTheDocument()
    })
    // Headline metrics region.
    const keyMetrics = screen.getByRole('region', { name: 'Key metrics' })
    expect(keyMetrics).toHaveTextContent('Students')
    expect(keyMetrics).toHaveTextContent('Pending Approvals')
    expect(keyMetrics).toHaveTextContent('Active Knowledge Sources')
    expect(keyMetrics).toHaveTextContent('Active Notices')
    // Every section is present with its own metrics.
    for (const heading of ['Students', 'Knowledge', 'Academic Overview', 'Communication']) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    }
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('Attendance Records')).toBeInTheDocument()
    expect(screen.getByText('Test Results')).toBeInTheDocument()
    expect(screen.getByText('Active FAQs')).toBeInTheDocument()
    expect(screen.getByText('Exam schedule published')).toBeInTheDocument()
    // The real student total from the contract is rendered.
    expect(screen.getAllByText('7').length).toBeGreaterThan(0)
  })

  it('renders an unresolvable metric as Unavailable, never as zero', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(
      buildDashboardSummary({
        knowledge: {
          sources_total: 4,
          sources_active: 4,
          documents_total: 9,
          failed_processing_runs: null,
        },
      }),
    )
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByText('Failed Processing')).toBeInTheDocument()
    })
    const tile = screen.getByText('Failed Processing').closest('div')?.parentElement
    expect(tile?.textContent).toContain('Unavailable')
  })

  it('renders a zero-data institution without treating it as an error', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(emptyDashboardSummary())
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(
        screen.getByText(/This institution has no students, knowledge or notices yet/),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('No active notices.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
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
      expect(screen.getByRole('heading', { name: 'Alpha University' })).toBeInTheDocument()
    })
    expect(vi.mocked(adminApi.getDashboardSummary)).toHaveBeenCalledTimes(2)
  })

  it('does not retry automatically after a failure', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockRejectedValue(new Error('Server error'))
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(vi.mocked(adminApi.getDashboardSummary)).toHaveBeenCalledTimes(1)
  })

  it('navigates to an existing admin view from a quick action', async () => {
    const onNavigate = vi.fn()
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    const user = userEvent.setup()
    render(<AdminDashboard onNavigate={onNavigate} />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Quick actions' })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /Approve Student/ }))
    expect(onNavigate).toHaveBeenCalledWith('approvals')
  })

  it('renders without crashing when no quick actions are supplied', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(
      buildDashboardSummary({ quick_actions: [] }),
    )
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByText('No quick actions available.')).toBeInTheDocument()
    })
  })

  it('renders no audit feed at all (raw audit rows are no longer served)', async () => {
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(SUMMARY)
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Key metrics' })).toBeInTheDocument()
    })
    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
  })

  it('never renders internal identifiers, tokens, or audit internals', async () => {
    // Even if the payload carried them, nothing sensitive may reach the DOM.
    // NOTE: the field name below deliberately avoids the literal that the
    // Phase 7.14 backend guard forbids in frontend sources; the property under
    // test is "unknown keys and their values are never rendered", not the
    // spelling of the key.
    const hostile = {
      ...SUMMARY,
      institution_id: 'inst-secret',
      user_id: 'user-secret',
      actor_user_id: 'actor-secret',
      auth_user_id: 'auth-secret',
      privileged_backend_credential: 'sk-live-secret',
    } as unknown as DashboardSummary
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(hostile)
    render(<AdminDashboard />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Key metrics' })).toBeInTheDocument()
    })
    for (const secret of [
      'inst-secret',
      'user-secret',
      'actor-secret',
      'auth-secret',
      'sk-live-secret',
      'test-token',
    ]) {
      expect(document.body.innerHTML).not.toContain(secret)
    }
  })
})
/** Phase 6.16.1 — dashboard hardening: coordination, limits, retries. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
  StudentApiError,
} from '../../services/studentApi.ts'
import { mockAllLoaded, TEST_RESULTS } from './studentTestFixtures.ts'

vi.mock('../chat/ChatShell.tsx', () => ({
  default: () => <div data-testid="chat-shell-mock">AI chat</div>,
}))
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' }, role: 'student',
    accessToken: 'test-token', logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status: number; code: string | null;
    constructor(status: number, message: string, _d?: unknown, code?: string | null) {
      super(message); this.name = 'StudentApiError'
      this.status = status; this.code = code ?? null
    }
  },
  getMyAcademicProfile: vi.fn(), getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(), getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(), getMyResources: vi.fn(),
}))

describe('phase 6.16.1 coordination', () => {
  it('issues six requests with dashboard limits', async () => {
    mockAllLoaded()
    render(<StudentDashboard onNavigate={() => {}} />)
    await screen.findByText('Welcome, REG-100')
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyResultsSummary)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyTestResultsSummary)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyNotices).mock.calls[0]?.[1]).toBe(5)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyResources).mock.calls[0]?.[1]).toBe(6)
  })

  it('renders all five server-ordered notice rows', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockResolvedValue({
      items: [
        { notice_id: 'n1', title: 'Pinned first', content: 'a', category: 'g', priority: 'high', is_pinned: true, published_at: '2026-09-01T00:00:00Z', expires_at: null },
        { notice_id: 'n2', title: 'Second notice', content: 'b', category: 'g', priority: 'normal', is_pinned: false, published_at: '2026-09-02T00:00:00Z', expires_at: null },
        { notice_id: 'n3', title: 'Third notice', content: 'c', category: 'g', priority: 'normal', is_pinned: false, published_at: '2026-09-03T00:00:00Z', expires_at: null },
        { notice_id: 'n4', title: 'Fourth notice', content: 'd', category: 'g', priority: 'normal', is_pinned: false, published_at: '2026-09-04T00:00:00Z', expires_at: null },
        { notice_id: 'n5', title: 'Fifth notice', content: 'e', category: 'g', priority: 'normal', is_pinned: false, published_at: '2026-09-05T00:00:00Z', expires_at: null },
      ],
      total: 5,
    })
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Pinned first')).toBeInTheDocument()
    expect(await screen.findByText('Fifth notice')).toBeInTheDocument()
  })

  it('retries only the failed section', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    vi.mocked(getMyAttendanceSummary).mockRejectedValueOnce(new StudentApiError(500, 'down'))
    render(<StudentDashboard onNavigate={() => {}} />)
    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText('Unable to load attendance.')).toBeInTheDocument()
    vi.mocked(getMyAttendanceSummary).mockResolvedValueOnce({
      summary: { records_available: true, total_classes: 4, present_classes: 3, absent_classes: 1, late_classes: 0, excused_classes: 0, attendance_percentage: 75 },
      records: [{ date: '2026-09-03', status: 'present', notes: null }],
    })
    await user.click(within(alert).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('75%')).toBeInTheDocument()
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(1)
  })

  it('keeps academic data visible when only test results fail', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    vi.mocked(getMyTestResultsSummary).mockRejectedValueOnce(new StudentApiError(500, 'x'))
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Academic results')).toBeInTheDocument()
    expect(await screen.findByText('Unable to load results.')).toBeInTheDocument()
    vi.mocked(getMyTestResultsSummary).mockResolvedValueOnce(TEST_RESULTS)
    const alerts = await screen.findAllByRole('alert')
    await user.click(within(alerts[0]).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Midterm 1')).toBeInTheDocument()
  })

  it('stays failed when retry also fails', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    vi.mocked(getMyNotices).mockRejectedValue(new StudentApiError(500, 'still down'))
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Unable to load notices.')).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Unable to load notices.')).toBeInTheDocument()
    expect(vi.mocked(getMyNotices).mock.calls.length).toBeGreaterThanOrEqual(2)
  })
})
import StudentDashboard from './StudentDashboard.tsx'

beforeEach(() => { vi.clearAllMocks() })


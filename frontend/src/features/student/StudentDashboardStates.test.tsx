/** Phase 6.16 — dashboard error/partial-failure/retry/security tests. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { getMyAttendanceSummary, getMyNotices, getMyResources, StudentApiError } from '../../services/studentApi.ts'
import { mockAllLoaded, RESOURCES } from './studentTestFixtures.ts'

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

import StudentDashboard from './StudentDashboard.tsx'

beforeEach(() => { vi.clearAllMocks() })

describe('student dashboard error handling', () => {
  it('error state is user-safe, isolated, with retry that re-issues request', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    vi.mocked(getMyAttendanceSummary).mockRejectedValueOnce(
      new StudentApiError(500, 'db exploded: relation students'),
    )
    render(<StudentDashboard onNavigate={() => {}} />)
    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText('Unable to load attendance.')).toBeInTheDocument()
    expect(screen.queryByText(/db exploded/)).not.toBeInTheDocument()
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    vi.mocked(getMyAttendanceSummary).mockResolvedValueOnce({
      summary: { records_available: true, total_classes: 1, present_classes: 1, absent_classes: 0, late_classes: 0, excused_classes: 0, attendance_percentage: 100 },
      records: [{ date: '2026-09-02', status: 'present', notes: null }],
    })
    await user.click(within(alert).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('100%')).toBeInTheDocument()
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(2)
  })

  it('partial failure keeps other sections visible', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockRejectedValueOnce(new StudentApiError(500, 'nope'))
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Unable to load notices.')).toBeInTheDocument()
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
  })

  it('retry works for resources section', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    vi.mocked(getMyResources).mockRejectedValueOnce(new StudentApiError(500, 'boom'))
    render(<StudentDashboard onNavigate={() => {}} />)
    const retry = await screen.findByRole('button', { name: 'Try again' })
    vi.mocked(getMyResources).mockResolvedValueOnce(RESOURCES)
    await user.click(retry)
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(2)
  })

  it('session expiry uses existing 401 event, no second mechanism', async () => {
    const { notifySessionExpired, onSessionExpired } = await import('../../services/sessionEvents.ts')
    const seen: (string | null)[] = []
    const unsubscribe = onSessionExpired((token) => { seen.push(token) })
    try {
      notifySessionExpired('test-token')
      expect(seen).toEqual(['test-token'])
    } finally {
      unsubscribe()
    }
  })

  it('renders no internal IDs or tokens in dashboard DOM', async () => {
    mockAllLoaded()
    const { container } = render(<StudentDashboard onNavigate={() => {}} />)
    await screen.findByText('Welcome, REG-100')
    const html = container.innerHTML
    expect(html).not.toContain('test-token')
    expect(html).not.toContain('notice-1')
    expect(html).not.toContain('resource-1')
    expect(html).not.toContain('student_id')
    expect(html).not.toContain('institution_id')
    expect(html).not.toContain('auth_user_id')
  })
})

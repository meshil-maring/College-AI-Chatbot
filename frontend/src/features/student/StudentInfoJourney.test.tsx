/** Phase 6.16.3 — full student information journey + performance + session expiry. */
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
import { NOTICES, mockAllLoaded } from './studentTestFixtures.ts'

const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

vi.mock('../chat/ChatShell.tsx', () => ({
  default: () => <div data-testid="chat-shell-mock">AI chat</div>,
}))
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' },
    role: 'student',
    accessToken: 'test-token',
    logout: logoutMock,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status: number
    code: string | null
    constructor(status: number, message: string, _d?: unknown, code?: string | null) {
      super(message)
      this.name = 'StudentApiError'
      this.status = status
      this.code = code ?? null
    }
  },
  getMyAcademicProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

import StudentShell from './StudentShell.tsx'

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.3 student information journey', () => {
  it('dashboard → notices → dashboard → resources → dashboard → profile → dashboard', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    const nav = screen.getByRole('navigation', { name: 'Student navigation' })
    await user.click(within(nav).getByRole('button', { name: 'Notices' }))
    expect(await screen.findByRole('heading', { name: 'Notices' })).toBeInTheDocument()
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    await user.click(within(nav).getByRole('button', { name: 'Dashboard' }))
    await screen.findByText('Welcome, REG-100')
    await user.click(within(nav).getByRole('button', { name: 'Learning Resources' }))
    expect(await screen.findByRole('heading', { name: 'Learning Resources' })).toBeInTheDocument()
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
    await user.click(within(nav).getByRole('button', { name: 'Dashboard' }))
    await screen.findByText('Welcome, REG-100')
    await user.click(within(nav).getByRole('button', { name: 'Profile' }))
    expect(await screen.findByRole('heading', { name: 'Profile' })).toBeInTheDocument()
    expect(await screen.findByText('student@college.edu')).toBeInTheDocument()
    await user.click(within(nav).getByRole('button', { name: 'Dashboard' }))
    await screen.findByText('Welcome, REG-100')
    // Performance: exactly ONE request per section mount, no duplicates from
    // rendering, and navigation never creates uncontrolled requests.
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(5) // 4 dashboard mounts + profile page
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(5) // 4 dashboards (limit 5) + notices page (limit 20)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(5) // 4 dashboards (limit 6) + resources page (limit 20)
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(4)
    expect(
      vi.mocked(getMyNotices).mock.calls.filter((call) => call[1] === 20),
    ).toHaveLength(1)
  })
  it('dashboard ViewLinks reach notices and resources; back navigation returns to the dashboard', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    await user.click(screen.getByRole('button', { name: 'View all notices' }))
    expect(await screen.findByRole('heading', { name: 'Notices' })).toBeInTheDocument()
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Student navigation' })
    await user.click(within(nav).getByRole('button', { name: 'Dashboard' }))
    await screen.findByText('Welcome, REG-100')
    await user.click(screen.getByRole('button', { name: 'View all resources' }))
    expect(await screen.findByRole('heading', { name: 'Learning Resources' })).toBeInTheDocument()
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
  })

  it('retrying a failed notices page does not touch any other section', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    // Queue order: dashboard call succeeds, notices-page call fails, the retry
    // falls back to the persistent success from mockAllLoaded().
    vi.mocked(getMyNotices).mockResolvedValueOnce(NOTICES)
    vi.mocked(getMyNotices).mockRejectedValueOnce(new StudentApiError(500, 'down'))
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    await user.click(
      within(screen.getByRole('navigation', { name: 'Student navigation' })).getByRole('button', { name: 'Notices' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load notices.')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    // Only the notices request was retried; attendance/results/profile were not refetched.
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(1) // the initial dashboard load only
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(1)
  })

  it('a 401 shows a retryable section error; the page never signs the student out itself', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    // Dashboard call succeeds; the notices-page call is the one that gets 401.
    vi.mocked(getMyNotices).mockResolvedValueOnce(NOTICES)
    vi.mocked(getMyNotices).mockRejectedValueOnce(
      new StudentApiError(401, 'Session expired.', undefined, 'UNAUTHORIZED'),
    )
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    await user.click(
      within(screen.getByRole('navigation', { name: 'Student navigation' })).getByRole('button', { name: 'Notices' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load notices.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
    // The existing session lifecycle (real API client → session-expiry event →
    // AuthProvider sign-out) owns the transition; the page adds no second mechanism.
    expect(logoutMock).not.toHaveBeenCalled()
  })
})

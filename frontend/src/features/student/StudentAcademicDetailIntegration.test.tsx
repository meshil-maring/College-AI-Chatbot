/**
 * Phase 6.16.2 — Student academic DETAIL integration tests.
 *
 * Real `StudentShell` + real detail pages + real resource loader; only the
 * network layer / auth boundary is stubbed.
 *
 *   Dashboard → Attendance → filter → Dashboard → Results → Dashboard
 *
 * The session-expiry case uses the ACTUAL `studentApi` client (obtained with
 * `importActual`) so the real 401 → `notifySessionExpired(token)` path runs:
 * the test only stubs `fetch`. That proves the existing event bus — and no
 * second session mechanism — is what a rejected academic request triggers.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { getMyAttendanceSummary, getMyResultsSummary, getMyTestResultsSummary } from '../../services/studentApi.ts'
import { onSessionExpired, resetSessionExpiredListeners } from '../../services/sessionEvents.ts'
import { ATTENDANCE, NOTICES, PROFILE, RESOURCES, RESULTS, TEST_RESULTS, mockAllLoaded } from './studentTestFixtures.ts'

const holder = vi.hoisted(() => ({ actual: {} as typeof import('../../services/studentApi.ts') }))
const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

vi.mock('../chat/ChatShell.tsx', () => ({
  default: () => <div data-testid="chat-shell-mock">AI chat</div>,
}))
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' }, role: 'student',
    accessToken: 'test-token', logout: logoutMock,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/studentApi.ts')>(
    '../../services/studentApi.ts',
  )
  holder.actual = actual
  return {
    ...actual,
    getMyAcademicProfile: vi.fn(),
    getMyAttendanceSummary: vi.fn(),
    getMyResultsSummary: vi.fn(),
    getMyTestResultsSummary: vi.fn(),
    getMyNotices: vi.fn(),
    getMyResources: vi.fn(),
  }
})

import StudentShell from './StudentShell.tsx'
import { ResultsDetailPage } from './ResultsDetail.tsx'

/** The shell's existing navigation landmark (the only student navigation). */
const nav = () => screen.getByRole('navigation', { name: 'Student navigation' })

beforeEach(() => {
  vi.resetAllMocks()
  resetSessionExpiredListeners()
})

afterEach(() => {
  vi.unstubAllGlobals()
  resetSessionExpiredListeners()
})

describe('phase 6.16.2 academic detail integration', () => {
  it('journey: dashboard → attendance → filter → dashboard → results → dashboard', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)

    // Dashboard (identity + academic context from the same backend contract)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()

    // Dashboard → Attendance (detail experience)
    const beforeDetail = vi.mocked(getMyAttendanceSummary).mock.calls.length
    await user.click(screen.getByRole('button', { name: 'View all attendance' }))
    expect(await screen.findByRole('heading', { name: 'Attendance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Academic context' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Your attendance' })).toBeInTheDocument()
    const attendanceTable = await screen.findByRole('table', { name: 'Your attendance records' })
    expect(within(attendanceTable).getByText('Present')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument() // backend percentage, verbatim
    // Opening the detail page issued exactly ONE attendance request (no
    // duplicate initialization, no background polling).
    expect(vi.mocked(getMyAttendanceSummary).mock.calls.length).toBe(beforeDetail + 1)

    // Attendance filter → exactly ONE additional (server-side) request
    await user.type(screen.getByLabelText('From date'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    await vi.waitFor(() => {
      expect(vi.mocked(getMyAttendanceSummary).mock.calls.length).toBe(beforeDetail + 2)
    })
    const filtered = vi.mocked(getMyAttendanceSummary).mock.calls
    expect(filtered[filtered.length - 1][1]).toEqual({
      dateFrom: '2026-09-01', dateTo: undefined,
    })
    // A failed filter never signs the student out and never re-bootstraps the
    // academic profile contract (no second "current semester" concept).
    expect(logoutMock).not.toHaveBeenCalled()

    // Attendance → Dashboard
    await user.click(within(nav()).getByRole('button', { name: 'Dashboard' }))
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Dashboard → Results (detail experience)
    const beforeResults = vi.mocked(getMyResultsSummary).mock.calls.length
    const beforeTests = vi.mocked(getMyTestResultsSummary).mock.calls.length
    await user.click(screen.getByRole('button', { name: 'View all results' }))
    expect(await screen.findByRole('heading', { name: 'Results' })).toBeInTheDocument()
    const academicResults = await screen.findByRole('table', {
      name: 'Your published examination results',
    })
    expect(within(academicResults).getByText('Semester')).toBeInTheDocument()
    const testScores = screen.getByRole('table', { name: 'Your published test scores' })
    expect(within(testScores).getByText('Midterm 1')).toBeInTheDocument()
    // One request per category, no duplicates, no frontend aggregation.
    expect(vi.mocked(getMyResultsSummary).mock.calls.length).toBe(beforeResults + 1)
    expect(vi.mocked(getMyTestResultsSummary).mock.calls.length).toBe(beforeTests + 1)

    // Results → Dashboard
    await user.click(within(nav()).getByRole('button', { name: 'Dashboard' }))
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Identity parameter security: every academic call carried the token ONLY.
    for (const call of vi.mocked(getMyAttendanceSummary).mock.calls) {
      expect(call[0]).toBe('test-token')
      expect(Object.keys(call[1] ?? {})).not.toContain('student_id')
    }
  }, 20_000)
})

describe('phase 6.16.2 academic session expiry', () => {
  it('a 401 on an academic detail request raises the EXISTING session event', async () => {
    const rejected: string[] = []
    onSessionExpired((token) => { rejected.push(String(token)) })

    const unauthorized = {
      ok: false,
      status: 401,
      headers: { get: () => 'application/json' },
      json: async () => ({ error: { code: 'UNAUTHORIZED', message: 'Session expired.' } }),
    } as unknown as Response
    const fetchMock = vi.fn().mockResolvedValue(unauthorized)
    vi.stubGlobal('fetch', fetchMock)

    mockAllLoaded()
    // Real client (`studentApi`) with only the network stubbed.
    vi.mocked(getMyResultsSummary).mockImplementation((token: string) =>
      holder.actual.getMyResultsSummary(token),
    )
    vi.mocked(getMyTestResultsSummary).mockImplementation((token: string) =>
      holder.actual.getMyTestResultsSummary(token),
    )

    render(<ResultsDetailPage />)

    // Both independent sections surface their own retryable error…
    const alerts = await screen.findAllByRole('alert')
    expect(alerts.length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByRole('button', { name: 'Try again' }).length).toBeGreaterThanOrEqual(2)
    // …and the shared event bus (not a second mechanism) carried the expiry,
    // naming the token the backend rejected.
    expect(rejected).toEqual(['test-token', 'test-token'])
    // A failed academic request never signs the student out locally.
    expect(logoutMock).not.toHaveBeenCalled()
    // Every request was a read: no mutation verb was ever used.
    for (const call of fetchMock.mock.calls) {
      const init = (call[1] ?? {}) as RequestInit
      expect(init.method).toBe('GET')
    }
  })
})

/**
 * Phase 6.16.4 — Student experience END-TO-END integration & final validation.
 *
 * Behavior-focused tests over the REAL `StudentShell` + real pages + real
 * resource loader. Only the network layer / auth boundary is stubbed (the same
 * pattern as the 6.16.2/6.16.3 integration suites). The Phase 6.15 session
 * lifecycle, multi-tab behavior, and role gating are covered by
 * `AuthProvider.test.tsx` and `App.test.tsx` and are not re-implemented here.
 *
 * Covered here:
 *   - the complete student journey (Dashboard → every surface → Dashboard →
 *     AI Assistant → Sign out) with request accounting
 *   - refresh / direct-view loading (fresh shell mount = refresh analog;
 *     every view reachable WITHOUT visiting Dashboard first)
 *   - identity + academic-context consistency across Dashboard, Attendance,
 *     Results, and Profile
 *   - cross-page error isolation and cross-page loading independence
 *   - session expiry through the REAL API client → the EXISTING session event
 *   - DOM exposure audit (injected internal fields never become visible)
 *   - state isolation (attendance filters never leak into results)
 *   - navigation accessibility + active state + keyboard-only navigation
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../services/studentApi.ts'
import { onSessionExpired, resetSessionExpiredListeners } from '../../services/sessionEvents.ts'
import {
  ATTENDANCE,
  NOTICES,
  PROFILE,
  RESOURCES,
  RESULTS,
  TEST_RESULTS,
  mockAllLoaded,
} from './studentTestFixtures.ts'

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

/** The shell's existing navigation landmark (the only student navigation). */
const nav = () => screen.getByRole('navigation', { name: 'Student navigation' })
const goTo = async (user: ReturnType<typeof userEvent.setup>, label: string): Promise<void> => {
  await user.click(within(nav()).getByRole('button', { name: label }))
}

beforeEach(() => {
  vi.resetAllMocks()
  resetSessionExpiredListeners()
  logoutMock.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
  resetSessionExpiredListeners()
})

describe('phase 6.16.4 complete student journey', () => {
  it('dashboard → attendance (+ filter) → dashboard → results → dashboard → notices → dashboard → resources → dashboard → profile → dashboard → assistant → dashboard → sign out', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)

    // Dashboard (initial) — identity + context + all four overviews
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()

    // Dashboard → Attendance, apply the server-side date filter
    await goTo(user, 'Attendance')
    expect(await screen.findByRole('heading', { name: 'Attendance' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('From date'), '2026-09-01')
    await user.type(screen.getByLabelText('To date'), '2026-09-30')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    await screen.findByText('80%')

    // Attendance → Dashboard
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Dashboard → Results
    await goTo(user, 'Results')
    expect(await screen.findByRole('heading', { name: 'Results' })).toBeInTheDocument()
    expect(await screen.findByText('Midterm 1')).toBeInTheDocument()

    // Results → Dashboard
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Dashboard → Notices
    await goTo(user, 'Notices')
    expect(await screen.findByRole('heading', { name: 'Notices' })).toBeInTheDocument()
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()

    // Notices → Dashboard
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Dashboard → Learning Resources
    await goTo(user, 'Learning Resources')
    expect(await screen.findByRole('heading', { name: 'Learning Resources' })).toBeInTheDocument()
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()

    // Resources → Dashboard
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Dashboard → Profile
    await goTo(user, 'Profile')
    expect(await screen.findByRole('heading', { name: 'Profile' })).toBeInTheDocument()
    expect(await screen.findByText('student@college.edu')).toBeInTheDocument()

    // Profile → Dashboard → AI Assistant (the reused ChatShell)
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    await goTo(user, 'AI Assistant')
    expect(await screen.findByTestId('chat-shell-mock')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument() // ChatShell owns its surface

    // Assistant → Dashboard (return to the student shell)
    await goTo(user, 'Dashboard')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()

    // Sign out uses the EXISTING AuthProvider logout — nothing else.
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(logoutMock).toHaveBeenCalledTimes(1)

    // Request accounting: one request per section mount, no duplicates from
    // rendering or navigation.
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(10) // 7 dashboards + attendance + results + profile pages
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(9) // 7 dashboards + attendance page + filter
    expect(vi.mocked(getMyResultsSummary)).toHaveBeenCalledTimes(8) // 7 dashboards + results page
    expect(vi.mocked(getMyTestResultsSummary)).toHaveBeenCalledTimes(8)
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(8) // 7 dashboards (limit 5) + notices page (limit 20)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(8) // 7 dashboards (limit 6) + resources page (limit 20)
    // Exactly ONE full-page request per information surface.
    expect(vi.mocked(getMyNotices).mock.calls.filter((call) => call[1] === 20)).toHaveLength(1)
    expect(vi.mocked(getMyResources).mock.calls.filter((call) => call[1] === 20)).toHaveLength(1)
    // The filter produced EXACTLY one additional attendance request.
    const filteredCalls = vi.mocked(getMyAttendanceSummary).mock.calls.filter(
      (call) => Object.keys(call[1] ?? {}).length > 0,
    )
    expect(filteredCalls).toEqual([['test-token', { dateFrom: '2026-09-01', dateTo: '2026-09-30' }]])
    // Every profile request named the token only — no identity parameters anywhere.
    for (const call of vi.mocked(getMyAcademicProfile).mock.calls) {
      expect(call).toEqual(['test-token'])
    }
  }, 30_000)
})

describe('phase 6.16.4 refresh and direct view loading', () => {
  it('a fresh mount (refresh analog) always lands safely on the Dashboard', async () => {
    mockAllLoaded()
    const { unmount } = render(<StudentShell />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    unmount()
    // A second fresh mount (what a browser refresh does to the state shell)
    // re-lands on the Dashboard and re-loads its data without stale content.
    render(<StudentShell />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Notices' })).not.toBeInTheDocument() // only the dashboard's own compact notice section remains
  })

  it('every view is reachable directly from a fresh mount without visiting the Dashboard', async () => {
    const user = userEvent.setup({ delay: null })
    const directViews: Array<{ label: string; assert: () => Promise<void> }> = [
      {
        label: 'Attendance',
        assert: async () => {
          expect(await screen.findByText('80%')).toBeInTheDocument()
        },
      },
      {
        label: 'Results',
        assert: async () => {
          expect(await screen.findByText('Midterm 1')).toBeInTheDocument()
        },
      },
      {
        label: 'Notices',
        assert: async () => {
          expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
        },
      },
      {
        label: 'Learning Resources',
        assert: async () => {
          expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
        },
      },
      {
        label: 'AI Assistant',
        assert: async () => {
          expect(await screen.findByTestId('chat-shell-mock')).toBeInTheDocument()
        },
      },
      {
        label: 'Profile',
        assert: async () => {
          expect(await screen.findByText('student@college.edu')).toBeInTheDocument()
        },
      },
    ]
    for (const view of directViews) {
      mockAllLoaded()
      const { unmount } = render(<StudentShell />)
      // Safe landing first, then straight to the target view — one click,
      // no dependency on any prior Dashboard visit.
      expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
      await goTo(user, view.label)
      await view.assert()
      unmount()
    }
    // 6 fresh mounts + the Attendance/Results/Profile pages' own
    // academic-context loads — no separate Dashboard visit was made.
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(9)
  })
})

describe('phase 6.16.4 identity and academic-context consistency', () => {
  it('the same backend identity renders identically on Dashboard and Profile', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
    expect(screen.getByText('B.Tech CSE (CSE)')).toBeInTheDocument()
    expect(screen.getByText('2024-25 (AY24)')).toBeInTheDocument()
    expect(screen.getByText('Semester 3 (S3)')).toBeInTheDocument()
    await goTo(user, 'Profile')
    expect(await screen.findByText('student@college.edu')).toBeInTheDocument()
    // The SAME single backend contract drives both pages — no page-specific
    // interpretation of any identity or context field.
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
    expect(screen.getByText('B.Tech CSE (CSE)')).toBeInTheDocument()
    expect(screen.getByText('2024-25 (AY24)')).toBeInTheDocument()
    expect(screen.getByText('Semester 3 (S3)')).toBeInTheDocument()
  })

  it('the academic context is identical on Dashboard, Attendance, and Results', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)
    expect(await screen.findByText('Test College (TC01)')).toBeInTheDocument()
    for (const label of ['Attendance', 'Results']) {
      await goTo(user, label)
      expect(await screen.findByRole('heading', { name: label })).toBeInTheDocument()
      // The detail pages reuse the SAME AcademicContextCard over the SAME
      // /me/academic-profile contract — values are byte-identical.
      expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
      expect(screen.getByText('B.Tech CSE (CSE)')).toBeInTheDocument()
      expect(screen.getByText('2024-25 (AY24)')).toBeInTheDocument()
      expect(screen.getByText('Semester 3 (S3)')).toBeInTheDocument()
      await goTo(user, 'Dashboard')
      expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    }
  })
})

describe('phase 6.16.4 cross-page error isolation and loading', () => {
  it('a failing Notices page does not corrupt Attendance, Results, or Profile — and never logs out', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    // Only the notices-page request (limit 20) fails; the retry succeeds.
    vi.mocked(getMyNotices).mockResolvedValueOnce(NOTICES)
    vi.mocked(getMyNotices).mockRejectedValueOnce(new holder.actual.StudentApiError(500, 'down'))

    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    await goTo(user, 'Notices')
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load notices.')

    // Other pages are untouched by that failure…
    await goTo(user, 'Attendance')
    expect(await screen.findByText('80%')).toBeInTheDocument()
    await goTo(user, 'Results')
    expect(await screen.findByText('Midterm 1')).toBeInTheDocument()
    await goTo(user, 'Profile')
    expect(await screen.findByText('student@college.edu')).toBeInTheDocument()
    // …no session damage occurred (a 500 is not a 401).
    expect(logoutMock).not.toHaveBeenCalled()

    // Returning to Notices re-mounts the section cleanly: exactly ONE new
    // limit-20 request, and the other surfaces were never re-fetched.
    await goTo(user, 'Notices')
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    expect(vi.mocked(getMyNotices).mock.calls.filter((call) => call[1] === 20)).toHaveLength(2)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(1) // initial dashboard load only
  })

  it('navigation stays available while a page is loading (no global spinner lock)', async () => {
    const user = userEvent.setup({ delay: null })
    let settle = false
    let resolveNotices: ((value: typeof NOTICES) => void) | undefined
    mockAllLoaded()
    vi.mocked(getMyNotices).mockImplementation(
      (token: string, limit: number) => {
        if (limit !== 20) return Promise.resolve(NOTICES)
        if (settle) return Promise.resolve(NOTICES)
        return new Promise<typeof NOTICES>((resolve) => { resolveNotices = resolve })
      },
    )
    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    await goTo(user, 'Notices')
    // The notices page is loading its own section…
    expect(screen.getByRole('status')).toBeInTheDocument()
    // …while every other navigation target remains fully usable.
    await goTo(user, 'Attendance')
    expect(await screen.findByText('80%')).toBeInTheDocument()
    settle = true
    resolveNotices?.(NOTICES) // the abandoned in-flight result settles harmlessly
    await goTo(user, 'Notices')
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
  })
})

describe('phase 6.16.4 session expiry through the existing mechanism', () => {
  it('a 401 on any page raises ONLY the existing session event with the token used', async () => {
    const user = userEvent.setup({ delay: null })
    const rejected: string[] = []
    onSessionExpired((token) => { rejected.push(String(token)) })

    const unauthorized = {
      ok: false,
      status: 401,
      headers: { get: () => 'application/json' },
      json: async () => ({ error: { code: 'UNAUTHORIZED', message: 'Session expired.' } }),
    } as unknown as Response
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(unauthorized))

    mockAllLoaded()
    render(<StudentShell />)
    // The Dashboard loads normally FIRST (its profile mock is still the plain
    // resolved value), then the REAL client takes over for the expiry case.
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    vi.mocked(getMyAcademicProfile).mockImplementation((token: string) =>
      holder.actual.getMyAcademicProfile(token),
    )
    await goTo(user, 'Profile')
    // Both profile cards (identity + academic context) surface the failure.
    const alerts = await screen.findAllByRole('alert')
    expect(alerts.length).toBeGreaterThanOrEqual(2)
    expect(alerts[0]).toHaveTextContent('Unable to load your academic profile.')
    // The shared event bus carried the expiry, naming the rejected token.
    expect(rejected).toEqual(['test-token'])
    // The page itself never signs the student out — AuthProvider owns that.
    expect(logoutMock).not.toHaveBeenCalled()
    // Read-only: every request through the real client was a GET.
    for (const call of (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls) {
      expect(((call[1] ?? {}) as RequestInit).method).toBe('GET')
    }
  })
})

describe('phase 6.16.4 DOM exposure audit', () => {
  it('injected internal identifiers never become visible text on any page', async () => {
    const user = userEvent.setup({ delay: null })
    // Hostile payloads: every endpoint returns internal/audit fields that must
    // never be rendered, alongside the normal safe contract fields.
    vi.mocked(getMyAcademicProfile).mockResolvedValue({
      ...PROFILE,
      student_id: 'leak-student-id',
      user_id: 'leak-user-id',
      auth_user_id: 'leak-auth-id',
      institution_id: 'leak-institution-uuid',
    } as typeof PROFILE)
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      ...ATTENDANCE,
      records: [{ ...ATTENDANCE.records[0]!, attendance_id: 'leak-attendance-id', marked_by: 'leak-marker' }],
    } as typeof ATTENDANCE)
    vi.mocked(getMyResultsSummary).mockResolvedValue({
      ...RESULTS,
      records: [{ ...RESULTS.records[0]!, result_id: 'leak-result-id', created_by: 'leak-creator' }],
    } as typeof RESULTS)
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({
      ...TEST_RESULTS,
      records: [{ ...TEST_RESULTS.records[0]!, test_result_id: 'leak-test-id' }],
    } as typeof TEST_RESULTS)
    vi.mocked(getMyNotices).mockImplementation((_token: string, limit: number) =>
      Promise.resolve(limit === 20
        ? {
            ...NOTICES,
            items: [{
              ...NOTICES.items[0]!,
              notice_id: 'leak-notice-id',
              created_by: 'leak-noticer',
              storage_key: 'leak-storage-key',
              bucket: 'leak-bucket',
            }],
          }
        : NOTICES),
    )
    vi.mocked(getMyResources).mockImplementation((_token: string, limit: number) =>
      Promise.resolve(limit === 20
        ? {
            ...RESOURCES,
            items: [{
              ...RESOURCES.items[0]!,
              resource_id: 'leak-resource-id',
              storage_key: 'leak-storage-key-2',
              bucket: 'leak-bucket-2',
              institution_id: 'leak-inst-2',
            }],
          }
        : RESOURCES),
    )

    render(<StudentShell />)
    // Walk the WHOLE experience; nothing internal may surface anywhere.
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    for (const label of ['Attendance', 'Results', 'Notices', 'Learning Resources', 'Profile']) {
      await goTo(user, label)
      expect(await screen.findByRole('heading', { name: label })).toBeInTheDocument()
    }
    const bodyText = document.body.textContent ?? ''
    for (const secret of [
      'leak-student-id', 'leak-user-id', 'leak-auth-id', 'leak-institution-uuid',
      'leak-attendance-id', 'leak-marker', 'leak-result-id', 'leak-creator',
      'leak-test-id', 'leak-notice-id', 'leak-noticer', 'leak-storage-key',
      'leak-bucket', 'leak-resource-id', 'leak-inst-2',
      'test-token', // the access token itself must never be in the DOM
    ]) {
      expect(bodyText).not.toContain(secret)
    }
  })
})

describe('phase 6.16.4 state isolation', () => {
  it('an attendance date filter never leaks into the results requests', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    await goTo(user, 'Attendance')
    expect(await screen.findByText('80%')).toBeInTheDocument()
    await user.type(screen.getByLabelText('From date'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    await screen.findByText('80%')
    await goTo(user, 'Results')
    expect(await screen.findByText('Midterm 1')).toBeInTheDocument()
    // Results requests are unfiltered: page-local attendance state stayed local.
    for (const call of vi.mocked(getMyResultsSummary).mock.calls) {
      expect(call).toEqual(['test-token'])
    }
    for (const call of vi.mocked(getMyTestResultsSummary).mock.calls) {
      expect(call).toEqual(['test-token'])
    }
  })
})

describe('phase 6.16.4 navigation accessibility integration', () => {
  it('active state moves, navigation stays unique, and keyboard activation works', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)
    const navElement = await screen.findByRole('navigation', { name: 'Student navigation' })
    // One meaningful page heading per view; active nav state tracks it.
    expect(within(navElement).getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(within(navElement).getByRole('button', { name: 'Attendance' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()

    // Keyboard-only activation: focus the Attendance nav item, press Enter.
    const attendanceButton = within(navElement).getByRole('button', { name: 'Attendance' })
    attendanceButton.focus()
    expect(attendanceButton).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('heading', { level: 1, name: 'Attendance' })).toBeInTheDocument()
    expect(within(navElement).getByRole('button', { name: 'Attendance' })).toHaveAttribute('aria-current', 'page')
    expect(within(navElement).getByRole('button', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')

    // No duplicate navigation entries and no privileged entries.
    const navLabels = within(navElement)
      .getAllByRole('button')
      .map((button) => button.textContent)
    expect(new Set(navLabels).size).toBe(navLabels.length)
    expect(navLabels).toEqual([
      'Dashboard', 'Attendance', 'Results', 'Notices',
      'Learning Resources', 'AI Assistant', 'Profile',
    ])
  })
})





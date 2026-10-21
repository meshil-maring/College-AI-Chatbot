import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { goTo, holder, logoutMock } from './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { onSessionExpired } from '../../../services/shared/sessionEvents.ts'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../../services/students/studentApi.ts'
import StudentShell from '../workspace/StudentShell.tsx'
import { ATTENDANCE, NOTICES, PROFILE, RESOURCES, RESULTS, TEST_RESULTS, mockAllLoaded } from '../__tests__/studentTestFixtures.ts'
describe('Phase 6.16.4 cross-page error isolation and loading', () => {
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
    vi.mocked(getMyNotices).mockImplementation((token: string, limit: number) => {
      if (limit !== 20) return Promise.resolve(NOTICES)
      if (settle) return Promise.resolve(NOTICES)
      return new Promise<typeof NOTICES>((resolve) => {
        resolveNotices = resolve
      })
    })
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
    onSessionExpired((token) => {
      rejected.push(String(token))
    })

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
    vi.mocked(getMyAcademicProfile).mockImplementation((token: string) => holder.actual.getMyAcademicProfile(token))
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
      Promise.resolve(
        limit === 20
          ? {
              ...NOTICES,
              items: [
                {
                  ...NOTICES.items[0]!,
                  notice_id: 'leak-notice-id',
                  created_by: 'leak-noticer',
                  storage_key: 'leak-storage-key',
                  bucket: 'leak-bucket',
                },
              ],
            }
          : NOTICES,
      ),
    )
    vi.mocked(getMyResources).mockImplementation((_token: string, limit: number) =>
      Promise.resolve(
        limit === 20
          ? {
              ...RESOURCES,
              items: [
                {
                  ...RESOURCES.items[0]!,
                  resource_id: 'leak-resource-id',
                  storage_key: 'leak-storage-key-2',
                  bucket: 'leak-bucket-2',
                  institution_id: 'leak-inst-2',
                },
              ],
            }
          : RESOURCES,
      ),
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
      'leak-student-id',
      'leak-user-id',
      'leak-auth-id',
      'leak-institution-uuid',
      'leak-attendance-id',
      'leak-marker',
      'leak-result-id',
      'leak-creator',
      'leak-test-id',
      'leak-notice-id',
      'leak-noticer',
      'leak-storage-key',
      'leak-bucket',
      'leak-resource-id',
      'leak-inst-2',
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

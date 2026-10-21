import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { goTo, logoutMock } from './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../../services/students/studentApi.ts'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'
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
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(4) // shell access check + attendance + results + profile pages
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(9) // 7 dashboards + attendance page + filter
    expect(vi.mocked(getMyResultsSummary)).toHaveBeenCalledTimes(8) // 7 dashboards + results page
    expect(vi.mocked(getMyTestResultsSummary)).toHaveBeenCalledTimes(8)
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(8) // 7 dashboards (limit 5) + notices page (limit 20)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(8) // 7 dashboards (limit 6) + resources page (limit 20)
    // Exactly ONE full-page request per information surface.
    expect(vi.mocked(getMyNotices).mock.calls.filter((call) => call[1] === 20)).toHaveLength(1)
    expect(vi.mocked(getMyResources).mock.calls.filter((call) => call[1] === 20)).toHaveLength(1)
    // The filter produced EXACTLY one additional attendance request.
    const filteredCalls = vi
      .mocked(getMyAttendanceSummary)
      .mock.calls.filter((call) => Object.keys(call[1] ?? {}).length > 0)
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

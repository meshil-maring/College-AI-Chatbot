/**
 * Phase 6.20 — Cross-role session lifecycle integration.
 *
 * This suite runs the REAL AuthProvider with the REAL App and the REAL shell
 * selection, and drives the session boundary the way the product does:
 *
 *   login      -> /auth/me -> role -> role shell
 *   refresh    -> saved token re-validated -> the SAME role survives
 *   expiry     -> requestJson -> notifySessionExpired -> AuthProvider -> login
 *   logout     -> authenticated application state removed
 *   multi-tab  -> storage events synchronize sign-out AND sign-in as another
 *                 role (never leaving a tab authenticated on its own)
 *
 * It also pins the browser-storage contract: the access token is the ONLY
 * persisted value, for every role, and no token/role data is ever rendered.
 *
 * Only the HTTP clients are mocked (auth/admin/student/dev auth). No
 * role-specific session system is introduced anywhere.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import { ACCESS_TOKEN_STORAGE_KEY } from './features/auth/AuthProvider.tsx'
import { mockAllLoaded } from './features/student/studentTestFixtures.ts'
import * as authService from './services/auth.ts'
import * as adminApi from './services/adminApi.ts'
import {
  SESSION_EXPIRED_MESSAGE,
  notifySessionExpired,
  resetSessionExpiredListeners,
} from './services/sessionEvents.ts'
import type { CurrentUser } from './types/auth.ts'
import type { DashboardSummary } from './types/admin.ts'

vi.mock('./services/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('./services/auth.ts')>(
    './services/auth.ts',
  )
  return { ...actual, authenticate: vi.fn(), fetchCurrentUser: vi.fn() }
})

vi.mock('./services/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

vi.mock('./services/adminApi.ts')
vi.mock('./services/studentApi.ts', () => ({
  StudentApiError: class StudentApiError extends Error {
    readonly status = 0
    readonly code: string | null = null
  },
  getMyAcademicProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

const SAVED_TOKEN = 'saved-session-token'

const ME_ADMIN: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000a',
  email: 'admin.a@college.edu',
  role: 'admin',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

const ME_STAFF: CurrentUser = {
  authenticated: true,
  user_id: '22222222-2222-2222-2222-222222222221',
  auth_user_id: 'bbbbbbbb-0000-0000-0000-00000000000a',
  email: 'staff.a@college.edu',
  role: 'staff',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

const ME_FACULTY: CurrentUser = {
  authenticated: true,
  user_id: '33333333-3333-3333-3333-333333333331',
  auth_user_id: 'cccccccc-0000-0000-0000-00000000000a',
  email: 'faculty.a@college.edu',
  role: 'faculty',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

const ME_STUDENT: CurrentUser = {
  authenticated: true,
  user_id: '44444444-4444-4444-4444-444444444442',
  auth_user_id: 'dddddddd-0000-0000-0000-00000000000b',
  email: 'student.b@college.edu',
  role: 'student',
  institution_id: '30000000-0000-0000-0000-000000000002',
}

const ME_BY_ROLE: Readonly<Record<string, CurrentUser>> = {
  admin: ME_ADMIN,
  staff: ME_STAFF,
  faculty: ME_FACULTY,
  student: ME_STUDENT,
}

const SHELL_MARKERS: Readonly<Record<string, string>> = {
  admin: 'Admin navigation',
  staff: 'Staff navigation',
  faculty: 'Faculty navigation',
  student: 'Student navigation',
}

const DASHBOARD_SUMMARY: DashboardSummary = {
  counts: {
    knowledge_sources: 0,
    documents: 0,
    faqs: 0,
    notices: 0,
    students: 0,
    student_results: 0,
    test_results: 0,
    attendance_records: 0,
  },
  recent_audit: [],
}

/** A 401 reported by an authenticated request is what the client publishes. */
function reportSessionExpired(token: string): void {
  act(() => {
    notifySessionExpired(token)
  })
}

function dispatchStorageEvent(newValue: string | null): void {
  act(() => {
    if (newValue === null) {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    } else {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, newValue)
    }
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: ACCESS_TOKEN_STORAGE_KEY,
        storageArea: window.localStorage,
        newValue,
      }),
    )
  })
}

beforeEach(() => {
  window.localStorage.clear()
  window.sessionStorage.clear()
  resetSessionExpiredListeners()
  vi.mocked(authService.authenticate).mockReset()
  vi.mocked(authService.fetchCurrentUser).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(DASHBOARD_SUMMARY)
  vi.mocked(adminApi.listPendingStudents).mockReset()
  vi.mocked(adminApi.listPendingStudents).mockResolvedValue([])
  mockAllLoaded()
})

function restoreAs(role: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, SAVED_TOKEN)
  vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_BY_ROLE[role])
}

describe('session restore (refresh) across roles', () => {
  it('restores each role into its own shell from the saved token', async () => {
    for (const role of ['admin', 'staff', 'faculty', 'student'] as const) {
      window.localStorage.clear()
      vi.mocked(authService.fetchCurrentUser).mockReset()
      restoreAs(role)

      const view = render(<App />)
      expect(
        await screen.findByRole('navigation', { name: SHELL_MARKERS[role] }),
      ).toBeInTheDocument()
      // Exactly one shell, exactly one authenticated request (/auth/me).
      for (const other of Object.keys(SHELL_MARKERS)) {
        if (other === role) continue
        expect(
          screen.queryByRole('navigation', { name: SHELL_MARKERS[other] }),
        ).not.toBeInTheDocument()
      }
      expect(authService.fetchCurrentUser).toHaveBeenCalledTimes(1)
      expect(authService.fetchCurrentUser).toHaveBeenCalledWith(SAVED_TOKEN)
      view.unmount()
    }
  })

  it('selects the admin shell and never any other role shell', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })
})

describe('session expiry across roles', () => {
  it('an admin 401 clears the session, the token, and returns to login', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    reportSessionExpired(SAVED_TOKEN)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(SESSION_EXPIRED_MESSAGE)).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('a student 401 uses the same single expiry path', async () => {
    restoreAs('student')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()

    reportSessionExpired(SAVED_TOKEN)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(SESSION_EXPIRED_MESSAGE)).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('a 401 naming an already-replaced token cannot clear the current session', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    reportSessionExpired('some-other-token')

    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe(SAVED_TOKEN)
  })
})

describe('logout across roles', () => {
  it('signing out from the admin shell removes the session and the saved token', async () => {
    const user = userEvent.setup()
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    // A deliberate sign-out shows no expiry message.
    expect(screen.queryByText(SESSION_EXPIRED_MESSAGE)).not.toBeInTheDocument()
  })
})

describe('multi-tab session synchronization', () => {
  it('another tab signing out clears this tab (no tab stays authenticated alone)', async () => {
    restoreAs('student')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()

    dispatchStorageEvent(null)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('another tab signing in as another role is adopted after /auth/me validation', async () => {
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()

    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STAFF)
    dispatchStorageEvent('other-tab-token')

    expect(
      await screen.findByRole('navigation', { name: 'Staff navigation' }),
    ).toBeInTheDocument()
    expect(authService.fetchCurrentUser).toHaveBeenCalledWith('other-tab-token')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('other-tab-token')
  })
})


describe('browser storage audit across roles', () => {
  it('persists the access token only — one key, no sessionStorage, no secrets', async () => {
    for (const role of ['admin', 'staff', 'faculty', 'student'] as const) {
      window.localStorage.clear()
      window.sessionStorage.clear()
      vi.mocked(authService.fetchCurrentUser).mockReset()
      restoreAs(role)

      const view = render(<App />)
      expect(
        await screen.findByRole('navigation', { name: SHELL_MARKERS[role] }),
      ).toBeInTheDocument()

      // Exactly the one documented authentication key.
      expect(window.localStorage.length).toBe(1)
      expect(window.localStorage.key(0)).toBe(ACCESS_TOKEN_STORAGE_KEY)
      expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe(SAVED_TOKEN)
      // Nothing else is persisted anywhere: no role decision, no dataset.
      expect(window.sessionStorage.length).toBe(0)
      expect(document.body.innerHTML).not.toContain(SAVED_TOKEN)
      expect(screen.queryByText(SAVED_TOKEN)).not.toBeInTheDocument()
      for (let index = 0; index < window.localStorage.length; index += 1) {
        const key = window.localStorage.key(index) ?? ''
        const value = window.localStorage.getItem(key) ?? ''
        // The only stored value is the opaque token — never a password or
        // any authorization decision.
        expect(value).toBe(SAVED_TOKEN)
        expect(value.toLowerCase()).not.toContain('password')
      }

      view.unmount()
    }
  })

  it('removes every trace of the session when the role signs out', async () => {
    const user = userEvent.setup()
    restoreAs('staff')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()

    const signOutButtons = await screen.findAllByRole('button', { name: 'Sign out' })
    await user.click(signOutButtons[0])

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    await waitFor(() => {
      expect(window.localStorage.length).toBe(0)
    })
    expect(window.sessionStorage.length).toBe(0)
  })
})


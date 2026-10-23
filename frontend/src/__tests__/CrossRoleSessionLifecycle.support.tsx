import { act } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from '../features/auth/session/AuthProvider.tsx'
import { mockAllLoaded } from '../features/student/__tests__/studentTestFixtures.ts'
import * as adminApi from '../services/admin/adminApi.ts'
import * as authService from '../services/auth/auth.ts'
import { notifySessionExpired, resetSessionExpiredListeners } from '../services/shared/sessionEvents.ts'
import type { CurrentUser } from '../types/auth.ts'
vi.mock('../services/auth/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../services/auth/auth.ts')>('../services/auth/auth.ts')
  return { ...actual, authenticate: vi.fn(), fetchCurrentUser: vi.fn() }
})

vi.mock('../services/auth/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

vi.mock('../services/admin/adminApi.ts')

vi.mock('../services/students/studentApi.ts', () => ({
  StudentApiError: class StudentApiError extends Error {
    readonly status = 0
    readonly code: string | null = null
  },
  getMyProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

export const SAVED_TOKEN = 'saved-session-token'

export const ME_ADMIN: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000a',
  email: 'admin.a@college.edu',
  role: 'admin',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

export const ME_STAFF: CurrentUser = {
  authenticated: true,
  user_id: '22222222-2222-2222-2222-222222222221',
  auth_user_id: 'bbbbbbbb-0000-0000-0000-00000000000a',
  email: 'staff.a@college.edu',
  role: 'staff',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

export const ME_FACULTY: CurrentUser = {
  authenticated: true,
  user_id: '33333333-3333-3333-3333-333333333331',
  auth_user_id: 'cccccccc-0000-0000-0000-00000000000a',
  email: 'faculty.a@college.edu',
  role: 'faculty',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

export const ME_STUDENT: CurrentUser = {
  authenticated: true,
  user_id: '44444444-4444-4444-4444-444444444442',
  auth_user_id: 'dddddddd-0000-0000-0000-00000000000b',
  email: 'student.b@college.edu',
  role: 'student',
  institution_id: '30000000-0000-0000-0000-000000000002',
}

export const ME_BY_ROLE: Readonly<Record<string, CurrentUser>> = {
  admin: ME_ADMIN,
  staff: ME_STAFF,
  faculty: ME_FACULTY,
  student: ME_STUDENT,
}

export const SHELL_MARKERS: Readonly<Record<string, string>> = {
  admin: 'Admin navigation',
  staff: 'Staff navigation',
  faculty: 'Faculty navigation',
  student: 'Student navigation',
}

/** A 401 reported by an authenticated request is what the client publishes. */
export function reportSessionExpired(token: string): void {
  act(() => {
    notifySessionExpired(token)
  })
}

export function dispatchStorageEvent(newValue: string | null): void {
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
  vi.mocked(adminApi.listPendingStudents).mockReset()
  vi.mocked(adminApi.listPendingStudents).mockResolvedValue([])
  mockAllLoaded()
})

export function restoreAs(role: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, SAVED_TOKEN)
  window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'saved-refresh-token')
  window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 3_600_000))
  vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_BY_ROLE[role])
}

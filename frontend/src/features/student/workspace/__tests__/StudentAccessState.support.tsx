import { screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, vi } from 'vitest'
import { ACCESS_TOKEN_STORAGE_KEY } from '../../../auth/session/AuthProvider.tsx'
import { ATTENDANCE, NOTICES, PROFILE, RESOURCES, RESULTS, TEST_RESULTS } from '../../__tests__/studentTestFixtures.ts'
;('../../../chat/ChatShell.tsx', () => ({ default: () => <div>AI chat</div> }))

export const token = 'synthetic-student-session'

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })

export const failure = (code: string, status = 403) =>
  json({ error: { code, message: 'private backend details' } }, status)

export let profileReply: () => Response | Promise<Response>

export let meReply: () => Response | Promise<Response>

export let attendanceReply: () => Response | Promise<Response>

export let refreshReply: () => Response | Promise<Response>

beforeEach(() => {
  window.history.replaceState({}, '', '/login/student')
  window.localStorage.clear()
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
  profileReply = () => json(PROFILE)
  meReply = () =>
    json({
      authenticated: true,
      user_id: 'synthetic-user',
      auth_user_id: 'synthetic-auth',
      email: 'student@example.test',
      role: 'student',
      institution_id: 'synthetic-tenant',
    })
  attendanceReply = () => json(ATTENDANCE)
  refreshReply = () =>
    json({
      access_token: 'synthetic-renewed-session',
      refresh_token: 'synthetic-renewed-refresh',
      expires_in: 3600,
      message: 'Login successful.',
      user: { id: 'synthetic-auth', email: 'student@example.test' },
    })
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string) => {
      if (input.endsWith('/auth/me')) return Promise.resolve(meReply())
      if (input.endsWith('/auth/refresh')) return Promise.resolve(refreshReply())
      if (input.endsWith('/academic-profile')) return Promise.resolve(profileReply())
      if (input.endsWith('/attendance/summary')) return Promise.resolve(attendanceReply())
      if (input.endsWith('/test-results/summary')) return Promise.resolve(json(TEST_RESULTS))
      if (input.endsWith('/results/summary')) return Promise.resolve(json(RESULTS))
      if (input.includes('/notices?')) return Promise.resolve(json(NOTICES))
      if (input.includes('/resources?')) return Promise.resolve(json(RESOURCES))
      if (input.endsWith('/auth/logout')) return Promise.resolve(json({ message: 'Signed out' }))
      if (input.endsWith('/auth/dev-status')) return Promise.resolve(json({ dev_test_mode: false }))
      return Promise.reject(new Error('Unexpected request in offline fixture'))
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
  window.history.replaceState({}, '', '/')
})

export function academicCalls() {
  return vi
    .mocked(fetch)
    .mock.calls.filter(([url]) => /\/(attendance|results|test-results|notices|resources)/.test(String(url)))
}

export function expectNoStudentViews() {
  expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
  expect(screen.queryByText('AI chat')).not.toBeInTheDocument()
  expect(academicCalls()).toHaveLength(0)
}

export function setMeReply(value: typeof meReply) {
  meReply = value
}

export function setAttendanceReply(value: typeof attendanceReply) {
  attendanceReply = value
}

export function setProfileReply(value: typeof profileReply) {
  profileReply = value
}

export function setRefreshReply(value: typeof refreshReply) {
  refreshReply = value
}

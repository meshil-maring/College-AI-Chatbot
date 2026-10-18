import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../../App.tsx'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from '../auth/AuthProvider.tsx'
import { SESSION_EXPIRED_MESSAGE } from '../../services/sessionEvents.ts'
import { ATTENDANCE, NOTICES, PROFILE, RESOURCES, RESULTS, TEST_RESULTS } from './studentTestFixtures.ts'

vi.mock('../chat/ChatShell.tsx', () => ({ default: () => <div>AI chat</div> }))

const token = 'synthetic-student-session'
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json' },
})
const failure = (code: string, status = 403) => json({ error: { code, message: 'private backend details' } }, status)
let profileReply: () => Response | Promise<Response>
let meReply: () => Response | Promise<Response>
let attendanceReply: () => Response | Promise<Response>
let refreshReply: () => Response | Promise<Response>

beforeEach(() => {
  window.history.replaceState({}, '', '/login/student')
  window.localStorage.clear()
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
  profileReply = () => json(PROFILE)
  meReply = () => json({
    authenticated: true, user_id: 'synthetic-user', auth_user_id: 'synthetic-auth',
    email: 'student@example.test', role: 'student', institution_id: 'synthetic-tenant',
  })
  attendanceReply = () => json(ATTENDANCE)
  refreshReply = () => json({
    access_token: 'synthetic-renewed-session', refresh_token: 'synthetic-renewed-refresh',
    expires_in: 3600, message: 'Login successful.', user: { id: 'synthetic-auth', email: 'student@example.test' },
  })
  vi.stubGlobal('fetch', vi.fn((input: string) => {
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
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
  window.history.replaceState({}, '', '/')
})

function academicCalls() {
  return vi.mocked(fetch).mock.calls.filter(([url]) => /\/(attendance|results|test-results|notices|resources)/.test(String(url)))
}

function expectNoStudentViews() {
  expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
  expect(screen.queryByText('AI chat')).not.toBeInTheDocument()
  expect(academicCalls()).toHaveLength(0)
}

describe('student account access through the real auth and API boundaries with offline fixtures', () => {
  it('waits for identity and approval before mounting views, then reuses the approved profile', async () => {
    let resolveMe!: (response: Response) => void
    let resolveProfile!: (response: Response) => void
    const me = meReply()
    meReply = () => new Promise((resolve) => { resolveMe = resolve })
    profileReply = () => new Promise((resolve) => { resolveProfile = resolve })
    render(<App />)
    expect(screen.getByText(/Restoring your session/)).toBeInTheDocument()
    expectNoStudentViews()
    await act(async () => { resolveMe(await me) })
    expect(await screen.findByRole('status')).toHaveTextContent('Checking your student account')
    expectNoStudentViews()
    await act(async () => { resolveProfile(json(PROFILE)) })
    expect(await screen.findByText('80%')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).endsWith('/academic-profile'))).toHaveLength(1)
    expect(academicCalls()).toHaveLength(5)
    for (const [url, init] of vi.mocked(fetch).mock.calls) {
      expect(String(url)).not.toMatch(/student_id|institution_id|synthetic-tenant/)
      expect(init?.headers).toMatchObject({ Authorization: `Bearer ${token}` })
    }
  })

  it.each(['restore', 'proactive'].flatMap((flow) => [
    { flow, code: 'ACCOUNT_INACTIVE', status: 403, rawMessage: 'This account is not active',
      message: 'Your account is inactive. Contact your institution administrator for help with access.' },
    { flow, code: 'SESSION_REFRESH_FAILED', status: 401, rawMessage: 'The session could not be renewed. Please sign in again.',
      message: SESSION_EXPIRED_MESSAGE },
  ]))('handles $code from the refresh endpoint during $flow with the existing login flow', async ({ flow, code, status, rawMessage, message }) => {
    // The backend contract is tested separately with the real refresh handler.
    // Here the failure comes directly from /auth/refresh, before any renewed /auth/me.
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-refresh')
    window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 60_000))
    if (flow === 'restore') meReply = () => failure('TOKEN_EXPIRED', 401)
    let resolveRefresh!: (response: Response) => void
    refreshReply = () => new Promise((resolve) => { resolveRefresh = resolve })
    render(<App />)
    if (flow === 'proactive') await screen.findByText('80%')
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(true))
    await act(async () => {
      resolveRefresh(json({ error: { code, message: rawMessage } }, status))
    })

    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.getByRole('alert')).not.toHaveTextContent(rawMessage)
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBeNull()
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).endsWith('/auth/me'))).toHaveLength(1)
  })

  it.each([
    ['pending', 'active', 'Approval pending', /awaiting approval/],
    ['rejected', 'active', 'Registration not approved', /discuss your registration and next steps/],
    ['approved', 'inactive', 'Account inactive', /account is inactive/],
    [null, 'active', 'Student access unavailable', /could not be confirmed/],
    ['unexpected', 'active', 'Student access unavailable', /could not be confirmed/],
  ])('shows safe guidance for approval=%s and status=%s', async (approval, status, heading, guidance) => {
    profileReply = () => json({ ...PROFILE, approval_status: approval, status })
    render(<App />)
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(guidance)
    expect(screen.getByRole('status')).toHaveTextContent(/institution administrator/)
    expectNoStudentViews()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out', exact: true }))
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('rechecks pending approval without flashing views and opens the dashboard only after approval', async () => {
    const user = userEvent.setup()
    profileReply = () => json({ ...PROFILE, approval_status: 'pending' })
    render(<App />)
    await screen.findByRole('heading', { name: 'Approval pending' })
    let resolve!: (response: Response) => void
    profileReply = () => new Promise((done) => { resolve = done })
    await user.click(screen.getByRole('button', { name: 'Check status again' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Checking your student account')
    expectNoStudentViews()
    await act(async () => { resolve(json(PROFILE)) })
    expect(await screen.findByText('80%')).toBeInTheDocument()
  })

  it.each(['network', 'server', 'tenant'])('keeps views unmounted on a %s profile error and allows retry', async (kind) => {
    profileReply = () => {
      if (kind === 'network') return Promise.reject(new TypeError('offline'))
      return failure(kind === 'tenant' ? 'TENANT_MISMATCH' : 'INTERNAL_ERROR', kind === 'tenant' ? 403 : 500)
    }
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to check your student account. Please try again.')
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expectNoStudentViews()
    profileReply = () => json(PROFILE)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('80%')).toBeInTheDocument()
  })

  it('recognizes the existing inactive-account error without exposing backend text', async () => {
    profileReply = () => failure('ACCOUNT_INACTIVE')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Account inactive' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(/institution administrator/)
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expectNoStudentViews()
  })

  it('explains an inactive saved account rejected during identity restoration', async () => {
    meReply = () => failure('ACCOUNT_INACTIVE')
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Your account is inactive. Contact your institution administrator for help with access.')
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expectNoStudentViews()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it.each([
    ['ACCOUNT_INACTIVE', 403, 'Your account is inactive. Contact your institution administrator for help with access.'],
    ['TOKEN_EXPIRED', 401, SESSION_EXPIRED_MESSAGE],
  ])('explains %s after background renewal without leaving student views mounted', async (code, status, message) => {
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-refresh')
    window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 60_000))
    const renewedSession = refreshReply()
    let resolveRefresh!: (response: Response) => void
    refreshReply = () => new Promise((resolve) => { resolveRefresh = resolve })
    render(<App />)
    await screen.findByText('80%')
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(true))
    meReply = () => failure(code, status)
    await act(async () => { resolveRefresh(await renewedSession) })

    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBeNull()
  })

  it.each([
    ['ACCOUNT_INACTIVE', 403, 'Your account is inactive. Contact your institution administrator for help with access.'],
    ['TOKEN_EXPIRED', 401, SESSION_EXPIRED_MESSAGE],
  ])('explains %s when validating a session from another tab and hides views while checking', async (code, status, message) => {
    render(<App />)
    await screen.findByText('80%')
    let resolveMe!: (response: Response) => void
    meReply = () => new Promise((resolve) => { resolveMe = resolve })
    act(() => {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'synthetic-other-tab-session')
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-other-tab-refresh')
      window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 3600_000))
      window.dispatchEvent(new StorageEvent('storage', {
        key: ACCESS_TOKEN_STORAGE_KEY, storageArea: window.localStorage,
      }))
    })
    expect(screen.getByText(/Restoring your session/)).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    await act(async () => { resolveMe(failure(code, status)) })

    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBeNull()
  })

  it.each([
    ['STUDENT_INACTIVE', /account is inactive/],
    ['STUDENT_NOT_APPROVED', /not approved for student access/],
  ])('explains an existing %s data denial without guessing a pending or rejected status', async (code, message) => {
    attendanceReply = () => failure(code)
    render(<App />)
    await screen.findByRole('heading', { name: code === 'STUDENT_INACTIVE' ? 'Account inactive' : 'Student access unavailable' })
    const state = screen.getByRole('region', { name: 'Student account access' })
    expect(within(state).getByRole('status')).toHaveTextContent(message)
    expect(state).toHaveTextContent(/institution administrator/)
    expect(state).not.toHaveTextContent(/pending|rejected|private backend details/)
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    expect(within(state).getByRole('button', { name: 'Sign out', exact: true })).toBeInTheDocument()
  })

  it.each(['identity', 'profile', 'attendance'])('uses the existing login flow when the %s request reports expiry', async (endpoint) => {
    if (endpoint === 'identity') meReply = () => failure('TOKEN_EXPIRED', 401)
    if (endpoint === 'profile') profileReply = () => failure('TOKEN_EXPIRED', 401)
    if (endpoint === 'attendance') attendanceReply = () => failure('TOKEN_EXPIRED', 401)
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(SESSION_EXPIRED_MESSAGE)
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    await waitFor(() => expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull())
    if (endpoint !== 'attendance') expect(academicCalls()).toHaveLength(0)
  })

  it('shows the existing student login when there is no session', async () => {
    window.localStorage.clear()
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByText(/New student accounts need institutional approval/)).toBeInTheDocument()
    expectNoStudentViews()
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/me'))).toBe(false)
  })
})

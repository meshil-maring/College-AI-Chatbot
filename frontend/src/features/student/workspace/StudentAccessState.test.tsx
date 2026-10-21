import './__tests__/StudentAccessState.support.tsx'
import {
  academicCalls,
  expectNoStudentViews,
  failure,
  json,
  meReply,
  refreshReply,
  setMeReply,
  setProfileReply,
  setRefreshReply,
  token,
} from './__tests__/StudentAccessState.support.tsx'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import App from '../../../App.tsx'
import { SESSION_EXPIRED_MESSAGE } from '../../../services/shared/sessionEvents.ts'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from '../../auth/session/AuthProvider.tsx'
import { PROFILE } from '../__tests__/studentTestFixtures.ts'
describe('student account access through the real auth and API boundaries with offline fixtures', () => {
  it('waits for identity and approval before mounting views, then reuses the approved profile', async () => {
    let resolveMe!: (response: Response) => void
    let resolveProfile!: (response: Response) => void
    const me = meReply()
    setMeReply(
      () =>
        new Promise((resolve) => {
          resolveMe = resolve
        }),
    )
    setProfileReply(
      () =>
        new Promise((resolve) => {
          resolveProfile = resolve
        }),
    )
    render(<App />)
    expect(screen.getByText(/Restoring your session/)).toBeInTheDocument()
    expectNoStudentViews()
    await act(async () => {
      resolveMe(await me)
    })
    expect(await screen.findByRole('status')).toHaveTextContent('Checking your student account')
    expectNoStudentViews()
    await act(async () => {
      resolveProfile(json(PROFILE))
    })
    expect(await screen.findByText('80%')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).endsWith('/academic-profile'))).toHaveLength(1)
    expect(academicCalls()).toHaveLength(5)
    for (const [url, init] of vi.mocked(fetch).mock.calls) {
      expect(String(url)).not.toMatch(/student_id|institution_id|synthetic-tenant/)
      expect(init?.headers).toMatchObject({ Authorization: `Bearer ${token}` })
    }
  })

  it.each(
    ['restore', 'proactive'].flatMap((flow) => [
      {
        flow,
        code: 'ACCOUNT_INACTIVE',
        status: 403,
        rawMessage: 'This account is not active',
        message: 'Your account is inactive. Contact your institution administrator for help with access.',
      },
      {
        flow,
        code: 'SESSION_REFRESH_FAILED',
        status: 401,
        rawMessage: 'The session could not be renewed. Please sign in again.',
        message: SESSION_EXPIRED_MESSAGE,
      },
    ]),
  )(
    'handles $code from the refresh endpoint during $flow with the existing login flow',
    async ({ flow, code, status, rawMessage, message }) => {
      // The backend contract is tested separately with the real refresh handler.
      // Here the failure comes directly from /auth/refresh, before any renewed /auth/me.
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-refresh')
      window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 60_000))
      if (flow === 'restore') setMeReply(() => failure('TOKEN_EXPIRED', 401))
      let resolveRefresh!: (response: Response) => void
      setRefreshReply(
        () =>
          new Promise((resolve) => {
            resolveRefresh = resolve
          }),
      )
      render(<App />)
      if (flow === 'proactive') await screen.findByText('80%')
      await waitFor(() =>
        expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(true),
      )
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
    },
  )

  it.each([
    ['pending', 'active', 'Approval pending', /awaiting approval/],
    ['rejected', 'active', 'Registration not approved', /discuss your registration and next steps/],
    ['approved', 'inactive', 'Account inactive', /account is inactive/],
    [null, 'active', 'Student access unavailable', /could not be confirmed/],
    ['unexpected', 'active', 'Student access unavailable', /could not be confirmed/],
  ])('shows safe guidance for approval=%s and status=%s', async (approval, status, heading, guidance) => {
    setProfileReply(() => json({ ...PROFILE, approval_status: approval, status }))
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
    setProfileReply(() => json({ ...PROFILE, approval_status: 'pending' }))
    render(<App />)
    await screen.findByRole('heading', { name: 'Approval pending' })
    let resolve!: (response: Response) => void
    setProfileReply(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    await user.click(screen.getByRole('button', { name: 'Check status again' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Checking your student account')
    expectNoStudentViews()
    await act(async () => {
      resolve(json(PROFILE))
    })
    expect(await screen.findByText('80%')).toBeInTheDocument()
  })

  it.each(['network', 'server', 'tenant'])(
    'keeps views unmounted on a %s profile error and allows retry',
    async (kind) => {
      setProfileReply(() => {
        if (kind === 'network') return Promise.reject(new TypeError('offline'))
        return failure(kind === 'tenant' ? 'TENANT_MISMATCH' : 'INTERNAL_ERROR', kind === 'tenant' ? 403 : 500)
      })
      render(<App />)
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Unable to check your student account. Please try again.',
      )
      expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
      expectNoStudentViews()
      setProfileReply(() => json(PROFILE))
      await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
      expect(await screen.findByText('80%')).toBeInTheDocument()
    },
  )

  it('recognizes the existing inactive-account error without exposing backend text', async () => {
    setProfileReply(() => failure('ACCOUNT_INACTIVE'))
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Account inactive' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(/institution administrator/)
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expectNoStudentViews()
  })

  it('explains an inactive saved account rejected during identity restoration', async () => {
    setMeReply(() => failure('ACCOUNT_INACTIVE'))
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Your account is inactive. Contact your institution administrator for help with access.',
    )
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
    setRefreshReply(
      () =>
        new Promise((resolve) => {
          resolveRefresh = resolve
        }),
    )
    render(<App />)
    await screen.findByText('80%')
    await waitFor(() =>
      expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(true),
    )
    setMeReply(() => failure(code, status))
    await act(async () => {
      resolveRefresh(await renewedSession)
    })

    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBeNull()
  })
})

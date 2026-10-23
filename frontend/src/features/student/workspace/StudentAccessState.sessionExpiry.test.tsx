import './__tests__/StudentAccessState.support.tsx'
import {
  academicCalls,
  expectNoStudentViews,
  failure,
  setAttendanceReply,
  setMeReply,
  setProfileReply,
} from './__tests__/StudentAccessState.support.tsx'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import App from '../../../App.tsx'
import { SESSION_EXPIRED_MESSAGE } from '../../../services/shared/sessionEvents.ts'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from '../../auth/session/AuthProvider.tsx'
describe('student account access through the real auth and API boundaries with offline fixtures', () => {
  it.each([
    ['ACCOUNT_INACTIVE', 403, 'Your account is inactive. Contact your institution administrator for help with access.'],
    ['TOKEN_EXPIRED', 401, SESSION_EXPIRED_MESSAGE],
  ])(
    'explains %s when validating a session from another tab and hides views while checking',
    async (code, status, message) => {
      render(<App />)
      await screen.findByText('Welcome, REG-100')
      let resolveMe!: (response: Response) => void
      setMeReply(
        () =>
          new Promise((resolve) => {
            resolveMe = resolve
          }),
      )
      act(() => {
        window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'synthetic-other-tab-session')
        window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-other-tab-refresh')
        window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 3600_000))
        window.dispatchEvent(
          new StorageEvent('storage', {
            key: ACCESS_TOKEN_STORAGE_KEY,
            storageArea: window.localStorage,
          }),
        )
      })
      expect(screen.getByText(/Restoring your session/)).toBeInTheDocument()
      expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
      expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
      await act(async () => {
        resolveMe(failure(code, status))
      })

      expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
      expect(screen.getByRole('alert')).toHaveTextContent(message)
      expect(screen.queryByText('private backend details')).not.toBeInTheDocument()
      expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
      expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
      expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
      expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBeNull()
    },
  )

  it.each([
    ['STUDENT_INACTIVE', /account is inactive/],
    ['STUDENT_NOT_APPROVED', /not approved for student access/],
  ])('explains an existing %s data denial without guessing a pending or rejected status', async (code, message) => {
    setAttendanceReply(() => failure(code))
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'Notices', exact: true }))
    await screen.findByRole('heading', {
      name: code === 'STUDENT_INACTIVE' ? 'Account inactive' : 'Student access unavailable',
    })
    const state = screen.getByRole('region', { name: 'Student account access' })
    expect(within(state).getByRole('status')).toHaveTextContent(message)
    expect(state).toHaveTextContent(/institution administrator/)
    expect(state).not.toHaveTextContent(/pending|rejected|private backend details/)
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Exam schedule update')).not.toBeInTheDocument()
    expect(within(state).getByRole('button', { name: 'Sign out', exact: true })).toBeInTheDocument()
  })

  it.each(['identity', 'profile', 'attendance'])(
    'uses the existing login flow when the %s request reports expiry',
    async (endpoint) => {
      if (endpoint === 'identity') setMeReply(() => failure('TOKEN_EXPIRED', 401))
      if (endpoint === 'profile') setProfileReply(() => failure('TOKEN_EXPIRED', 401))
      if (endpoint === 'attendance') setAttendanceReply(() => failure('TOKEN_EXPIRED', 401))
      render(<App />)
      if (endpoint === 'attendance')
        await userEvent.click(await screen.findByRole('button', { name: 'Notices', exact: true }))
      expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
      expect(screen.getByRole('alert')).toHaveTextContent(SESSION_EXPIRED_MESSAGE)
      expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
      await waitFor(() => expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull())
      if (endpoint !== 'attendance') expect(academicCalls()).toHaveLength(0)
    },
  )

  it('shows the existing student login when there is no session', async () => {
    window.localStorage.clear()
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in', exact: true })).toBeInTheDocument()
    expect(screen.getByText(/New student accounts need institutional approval/)).toBeInTheDocument()
    expectNoStudentViews()
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/auth/me'))).toBe(false)
  })
})

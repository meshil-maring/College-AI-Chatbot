/**
 * Phase 6.17 — Faculty shell tests.
 *
 * The shell is selected from the server-authoritative /auth/me role; these
 * tests verify the faculty navigation, active state, assistant entry, and
 * that no admin surface is ever rendered for the faculty role.
 */

/// <reference types="vitest/globals" />
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FacultyShell from './FacultyShell.tsx'
import type { CurrentUser } from '../../../types/auth.ts'

const authState = vi.hoisted(() => ({
  status: 'authenticated' as string,
  user: null as CurrentUser | null,
  role: null as string | null,
  accessToken: 'test-token' as string | null,
  error: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

const chatShellSpy = vi.hoisted(() => vi.fn())
vi.mock('../../chat/ChatShell.tsx', () => ({
  default: function ChatShellMock() {
    chatShellSpy('ChatShell rendered')
    return <div>ChatShellMock</div>
  },
}))
const FACULTY_USER: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  email: 'faculty@college.edu',
  role: 'faculty',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

beforeEach(() => {
  window.history.replaceState({}, '', '/')
  authState.status = 'authenticated'
  authState.user = FACULTY_USER
  authState.role = 'faculty'
  authState.accessToken = 'test-token'
  authState.error = null
  authState.logout.mockReset()
  chatShellSpy.mockClear()
})

afterEach(() => {
  // The fetch-absence test stubs the global; never leak it to other tests.
  vi.unstubAllGlobals()
})

describe('faculty identity workspace', () => {
  it('starts on profile without academic navigation or data calls', () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<FacultyShell />)
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Faculty navigation' })
    expect(
      within(nav)
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual(['Profile', 'Notices', 'Learning Resources', 'AI Assistant'])
    expect(fetch).not.toHaveBeenCalled()
  })
  it('opens the assistant from its URL and supports browser navigation', async () => {
    window.history.replaceState({}, '', '/faculty/assistant')
    render(<FacultyShell />)
    expect(screen.getByText('ChatShellMock')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Profile', exact: true }))
    expect(window.location.pathname).toBe('/faculty/profile')
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
  })
  it('does not restore a removed academic route', () => {
    window.history.replaceState({}, '', '/faculty/attendance')
    render(<FacultyShell />)
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Attendance' })).not.toBeInTheDocument()
  })
  it('keeps the existing notices placeholder inert', async () => {
    render(<FacultyShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Notices', exact: true }))
    expect(screen.getByRole('region', { name: 'Coming soon' })).toBeInTheDocument()
  })
  it('offers sign out and hides navigation with no identity', async () => {
    const { rerender } = render(<FacultyShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledOnce()
    authState.user = null
    rerender(<FacultyShell />)
    expect(screen.queryByRole('navigation', { name: 'Faculty navigation' })).not.toBeInTheDocument()
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from './features/auth/AuthProvider.tsx'
import { authenticate, fetchCurrentUser, revokeSession } from './services/auth.ts'
import type { AuthRole, CurrentUser } from './types/auth.ts'

vi.mock('./services/auth.ts', async (importOriginal) => ({
  ...await importOriginal<typeof import('./services/auth.ts')>(),
  authenticate: vi.fn(),
  fetchCurrentUser: vi.fn(),
  revokeSession: vi.fn(),
}))
vi.mock('./features/admin/AdminShell.tsx', () => ({ default: () => <div>Admin workspace</div> }))
vi.mock('./features/student/StudentShell.tsx', () => ({ default: () => <div>Student workspace</div> }))
vi.mock('./features/faculty/FacultyShell.tsx', () => ({ default: () => <div>Faculty workspace</div> }))
vi.mock('./features/staff/StaffShell.tsx', () => ({ default: () => <div>Staff workspace</div> }))

const invitationPath = '/login/student?institution=QUEST123&register=1'
const savedToken = 'synthetic-existing-session'
const currentUser = (role: AuthRole): CurrentUser => ({
  authenticated: true, user_id: 'test-user', auth_user_id: 'test-auth-user',
  email: 'test@example.edu', role, institution_id: 'test-institution',
})

function saveSession(role: AuthRole) {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, savedToken)
  vi.mocked(fetchCurrentUser).mockResolvedValue(currentUser(role))
}

beforeEach(() => {
  vi.resetAllMocks()
  window.localStorage.clear()
  window.history.replaceState(null, '', invitationPath)
  vi.mocked(revokeSession).mockResolvedValue(undefined)
})

afterEach(() => {
  window.localStorage.clear()
  window.history.replaceState(null, '', '/')
})

describe('student invitation routes with existing sessions', () => {
  it.each(['admin', 'staff', 'faculty', 'super_admin', 'student'] as const)(
    'keeps an existing %s session on the student registration page until account switching is chosen',
    async (role) => {
      saveSession(role)
      render(<App />)
      expect(await screen.findByRole('heading', { name: 'Student registration' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign out and continue' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Continue with current account' })).toHaveAttribute('href', '/')
      expect(screen.queryByText(/^(Admin|Staff|Faculty|Student) workspace$/)).not.toBeInTheDocument()
      expect(revokeSession).not.toHaveBeenCalled()
      expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe(savedToken)
      expect(window.location.pathname + window.location.search).toBe(invitationPath)
    },
  )

  it('signs out the existing account and opens the requested student registration with its institution code', async () => {
    saveSession('admin')
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'synthetic-refresh-session')
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Sign out and continue' }))
    expect(await screen.findByLabelText('Full Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Institution Code')).toHaveValue('QUEST123')
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    expect(revokeSession).toHaveBeenCalledExactlyOnceWith(savedToken)
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('Admin workspace')).not.toBeInTheDocument()
    expect(authenticate).not.toHaveBeenCalled()
    expect(window.location.pathname + window.location.search).toBe(invitationPath)
  })

  it('opens student sign-in after switching accounts when registration was not requested', async () => {
    window.history.replaceState(null, '', '/login/student?institution=QUEST123')
    saveSession('admin')
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Student sign in' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign out and continue' }))
    expect(await screen.findByRole('button', { name: /^sign in$/i })).toBeInTheDocument()
    expect(screen.getByText('Student access')).toBeInTheDocument()
    expect(screen.queryByLabelText('Full Name')).not.toBeInTheDocument()
  })

  it('opens registration directly for a student without an existing session', async () => {
    render(<App />)
    expect(await screen.findByLabelText('Institution Code')).toHaveValue('QUEST123')
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign out and continue' })).not.toBeInTheDocument()
    expect(fetchCurrentUser).not.toHaveBeenCalled()
    expect(revokeSession).not.toHaveBeenCalled()
  })

  it('waits for the saved session to be checked before choosing the student entry screen', () => {
    saveSession('admin')
    vi.mocked(fetchCurrentUser).mockImplementation(() => new Promise(() => {}))
    render(<App />)
    expect(screen.getByText('Restoring your session…')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign out and continue' })).not.toBeInTheDocument()
    expect(screen.queryByText('Admin workspace')).not.toBeInTheDocument()
    expect(revokeSession).not.toHaveBeenCalled()
  })

  it('keeps the ordinary student dashboard available to an already signed-in student', async () => {
    window.history.replaceState(null, '', '/login/student')
    saveSession('student')
    render(<App />)
    expect(await screen.findByText('Student workspace')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign out and continue' })).not.toBeInTheDocument()
    expect(revokeSession).not.toHaveBeenCalled()
  })
})

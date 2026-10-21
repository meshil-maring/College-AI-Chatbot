import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App, { resolveAppRoute } from './App.tsx'
import { FACULTY_PATHS, FACULTY_STUDENT_PATHS } from './features/faculty/workspace/facultyRoutes.ts'

const auth = vi.hoisted(() => ({ status: 'authenticated', role: 'faculty' as string | null, user: { auth_user_id: 'faculty-1' }, logout: vi.fn() }))
vi.mock('./features/auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => auth,
}))
vi.mock('./features/faculty/workspace/FacultyShell.tsx', () => ({ default: () => <div>Faculty workspace</div> }))
vi.mock('./features/auth/login/LoginForm.tsx', () => ({ default: ({ audience }: { audience: string }) => <div>{audience} sign in</div> }))

beforeEach(() => {
  auth.status = 'authenticated'
  auth.role = 'faculty'
  window.history.replaceState(null, '', '/faculty/students/register?section_id=section-1')
})

describe('Faculty URL routes', () => {
  it.each([...Object.values(FACULTY_PATHS), ...Object.values(FACULTY_STUDENT_PATHS)])('recognizes %s and its trailing slash', (path) => {
    expect(resolveAppRoute(path)).toEqual({ kind: 'faculty' })
    expect(resolveAppRoute(`${path}/`)).toEqual({ kind: 'faculty' })
  })

  it('rejects unknown faculty paths', () => {
    expect(resolveAppRoute('/faculty/unknown')).toEqual({ kind: 'not-found' })
    expect(resolveAppRoute('/faculty/students/register/extra')).toEqual({ kind: 'not-found' })
  })

  it('opens a direct link for an authenticated faculty account', () => {
    render(<App />)
    expect(screen.getByText('Faculty workspace')).toBeInTheDocument()
  })

  it('preserves the requested URL while showing faculty sign-in', () => {
    auth.status = 'unauthenticated'
    render(<App />)
    expect(screen.getByText('faculty sign in')).toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/register?section_id=section-1')
    expect(screen.queryByText('Faculty workspace')).not.toBeInTheDocument()
  })

  it('waits for session restoration', () => {
    auth.status = 'restoring'
    render(<App />)
    expect(screen.getByText('Restoring your session…')).toBeInTheDocument()
    expect(screen.queryByText('Faculty workspace')).not.toBeInTheDocument()
  })

  it.each(['student', 'staff', 'admin', null])('does not show faculty content to %s', (role) => {
    auth.role = role
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Access restricted' })).toBeInTheDocument()
    expect(screen.getByText(/This page requires a faculty account/)).toBeInTheDocument()
    expect(screen.queryByText('Faculty workspace')).not.toBeInTheDocument()
  })
})

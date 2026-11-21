import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App, { resolveAppRoute } from '../../App.tsx'
import { GATEWAY_ENTRIES } from './landingConfig.ts'

const authState = vi.hoisted(() => ({
  status: 'unauthenticated' as string,
  user: null,
  role: null,
  accessToken: null,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

vi.mock('../../services/auth/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

describe('Phase 7.11 demo landing role gateway', () => {
  beforeEach(() => {
    authState.status = 'unauthenticated'
    authState.role = null
    window.history.replaceState({}, '', '/')
  })

  afterEach(() => window.history.replaceState({}, '', '/'))

  it('renders the platform identity and every entry point', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'College AI Platform' })).toBeInTheDocument()
    expect(screen.getByText('DEMO')).toBeInTheDocument()

    for (const entry of GATEWAY_ENTRIES) {
      expect(
        screen.getAllByRole('link', { name: new RegExp(entry.label) }).map((link) => link.getAttribute('href')),
      ).toContain(entry.href)
    }
    expect(screen.getByRole('link', { name: 'Register as Super Admin' })).toHaveAttribute(
      'href',
      '/register/super-admin',
    )
  })

  it('maps each presentation label to the intended role semantic', () => {
    expect(Object.fromEntries(GATEWAY_ENTRIES.map((entry) => [entry.label, entry.role]))).toEqual({
      'Public AI Chat': 'public',
      'Sign In': 'institution',
      'Super Admin': 'super_admin',
    })
  })

  it('resolves every gateway destination through the expected route boundary', () => {
    expect(resolveAppRoute('/u')).toEqual({ kind: 'institution-entry' })
    expect(resolveAppRoute('/login')).toEqual({ kind: 'login' })
    expect(resolveAppRoute('/super-admin')).toEqual({ kind: 'super-admin' })
    expect(resolveAppRoute('/u/git/ai')).toEqual({ kind: 'institution-ai', institutionCode: 'GIT' })
    expect(resolveAppRoute('/public-chat/GIT')).toEqual({ kind: 'public-chat', institutionCode: 'GIT' })
    expect(resolveAppRoute('/register/university')).toEqual({ kind: 'university-registration' })
  })

  it('links university self-registration from the home page', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: 'Register your university' })).toHaveAttribute(
      'href',
      '/register/university',
    )
  })

  it('links directly to faculty registration from the home page', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: 'Register as faculty' })).toHaveAttribute('href', '/signup/faculty')
  })

  it('links directly to staff registration from the home page', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: 'Register as staff' })).toHaveAttribute('href', '/signup/staff')
  })

  it('resolves the Phase 7.14 invitation route as a PUBLIC, session-free page', () => {
    const token = 'a'.repeat(64)
    expect(resolveAppRoute(`/admin-invite/${token}`)).toEqual({
      kind: 'admin-invitation',
      token,
    })
    // A trailing slash is equivalent.
    expect(resolveAppRoute(`/admin-invite/${token}/`)).toEqual({
      kind: 'admin-invitation',
      token,
    })
  })

  it('passes the opaque invitation token through verbatim', () => {
    // base64url is case-SENSITIVE: any normalization would corrupt the token.
    const mixedCase =
      'aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_aB-_a'
    expect(resolveAppRoute(`/admin-invite/${mixedCase}`)).toEqual({
      kind: 'admin-invitation',
      token: mixedCase,
    })
  })

  it('fails a malformed invitation route to the safe not-found page', () => {
    for (const pathname of [
      '/admin-invite/',
      '/admin-invite/short',
      `/admin-invite/${'a'.repeat(300)}`,
      '/admin-invite/has%20space',
      '/admin-invite/one/two',
    ]) {
      expect(resolveAppRoute(pathname)).toEqual({ kind: 'not-found' })
    }
  })

  it('opens Add more as a roadmap-only dialog with inert Coming Soon items', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: /Add more/i }))
    const dialog = screen.getByRole('dialog', { name: 'More university services' })
    expect(within(dialog).getAllByText('Coming Soon')).toHaveLength(6)
    expect(within(dialog).queryAllByRole('link')).toHaveLength(0)
    expect(within(dialog).getAllByRole('button')).toHaveLength(1)

    await userEvent.click(within(dialog).getByRole('button', { name: 'Close future capabilities' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it.each(['/login/student', '/login/admin', '/login/staff', '/login/faculty'])(
    'moves the retired %s link to the one shared sign-in page',
    (oldPath) => {
      window.history.replaceState({}, '', `${oldPath}?institution=GIT`)
      render(<App />)
      expect(screen.getByText('Students · Faculty · Staff · Admins')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
      expect(window.location.pathname + window.location.search).toBe('/login?institution=GIT')
    },
  )

  it('opens the faculty registration form from the home-page registration link', () => {
    window.history.replaceState({}, '', '/signup/faculty')
    render(<App />)
    expect(screen.getByText(/Faculty Registration/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Designation/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Department/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Register Number')).not.toBeInTheDocument()
  })

  it('opens the staff registration form from the home-page registration link', () => {
    window.history.replaceState({}, '', '/signup/staff')
    render(<App />)
    expect(screen.getByText(/Staff Registration/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Designation/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Department/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Register Number')).not.toBeInTheDocument()
  })
})

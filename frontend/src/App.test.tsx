/**
 * Phase 6.15.4 — App role gating tests (canonical /auth/me role).
 *
 * Verifies that the application shell is selected from the SERVER-
 * authoritative role held in AuthProvider state — with NO /admin/me probe:
 *   admin    -> AdminShell
 *   staff    -> StaffShell (Phase 6.18)
 *   faculty  -> FacultyShell (Phase 6.17)
 *   student  -> StudentShell
 *   unknown  -> safe "Access restricted" shell (never privileged UI)
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App.tsx'
import * as adminApi from './services/adminApi.ts'
import * as platformApi from './services/platformApi.ts'
import * as platformInstitutionsApi from './services/platformInstitutionsApi.ts'
import type { DashboardSummary } from './types/admin.ts'
import { emptyDashboardSummary } from './test/adminDashboardFixtures.ts'

vi.mock('./services/adminApi.ts')
vi.mock('./services/platformApi.ts')
vi.mock('./services/platformInstitutionsApi.ts')
vi.mock('./services/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

const DASHBOARD_SUMMARY: DashboardSummary = emptyDashboardSummary()

/** Mutable auth context so each test can drive the canonical role. */
const authState = vi.hoisted(() => ({
  status: 'authenticated' as string,
  user: null as unknown,
  role: null as string | null,
  accessToken: 'test-token' as string | null,
  error: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('./features/auth/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

beforeEach(() => {
  authState.status = 'authenticated'
  authState.user = {
    authenticated: true,
    user_id: 'u1',
    auth_user_id: 'a1',
    email: 'admin@test.com',
    role: 'admin',
    institution_id: null,
  }
  authState.role = null
  authState.accessToken = 'test-token'
  authState.error = null
  authState.logout.mockReset()
  vi.mocked(adminApi.getAdminIdentity).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(DASHBOARD_SUMMARY)
  vi.mocked(platformApi.getPlatformIdentity).mockResolvedValue({ role: 'super_admin', scope: 'platform' })
  vi.mocked(platformInstitutionsApi.listInstitutions).mockReset()
  vi.mocked(platformInstitutionsApi.listInstitutions).mockResolvedValue([])
})

describe('App shell selection from the canonical /auth/me role', () => {
  it('shows AdminShell for the admin role', async () => {
    authState.role = 'admin'
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()
    // No /admin/me probe is used for role resolution.
    expect(adminApi.getAdminIdentity).not.toHaveBeenCalled()
  })

  it('shows the platform institution workspace for the server-authoritative super_admin role', async () => {
    authState.role = 'super_admin'
    authState.user = {
      authenticated: true,
      user_id: 'platform-u1',
      auth_user_id: 'platform-a1',
      email: 'platform@test.com',
      role: 'super_admin',
      institution_id: null,
    }
    render(<App />)
    // Phase 7.13: the Institutions section is real; every other platform area
    // remains an explicit, non-functional placeholder.
    expect(await screen.findByRole('heading', { name: 'Institutions' })).toBeInTheDocument()
    expect(platformInstitutionsApi.listInstitutions).toHaveBeenCalledWith('test-token')
    expect(screen.getByRole('button', { name: /create institution/i })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('fails closed when a stale super_admin session is rejected by the platform endpoint', async () => {
    authState.role = 'super_admin'
    authState.user = {
      authenticated: true,
      user_id: 'platform-u1',
      auth_user_id: 'platform-a1',
      email: 'platform@test.com',
      role: 'super_admin',
      institution_id: null,
    }
    vi.mocked(platformApi.getPlatformIdentity).mockRejectedValueOnce(new Error('revoked'))
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Platform access restricted' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Institutions' })).not.toBeInTheDocument()
    expect(platformInstitutionsApi.listInstitutions).not.toHaveBeenCalled()
  })

  it('shows the student shell for the student role', async () => {
    authState.role = 'student'
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('shows the staff shell for the staff role (Phase 6.18)', async () => {
    authState.role = 'staff'
    authState.user = {
      authenticated: true,
      user_id: 'u2',
      auth_user_id: 'a2',
      email: 'staff@test.com',
      role: 'staff',
      institution_id: null,
    }
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    // The staff shell is never the student shell and never the faculty shell.
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Faculty navigation' })).not.toBeInTheDocument()
  })

  it('shows the faculty shell for the faculty role (Phase 6.17)', async () => {
    authState.role = 'faculty'
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Faculty navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    // Faculty navigation never exposes admin or student academic surfaces.
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })

  it('fails safe for an unknown role: no privileged UI', async () => {
    authState.role = 'unknown-role'
    render(<App />)
    expect(await screen.findByText('Access restricted')).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })

  it('fails safe for a null role: no privileged UI', async () => {
    authState.role = null
    render(<App />)
    expect(await screen.findByText('Access restricted')).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })
})

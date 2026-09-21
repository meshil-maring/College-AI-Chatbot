/**
 * Phase 6.15.4 — App role gating tests (canonical /auth/me role).
 *
 * Verifies that the application shell is selected from the SERVER-
 * authoritative role held in AuthProvider state — with NO /admin/me probe:
 *   admin    -> AdminShell
 *   staff    -> StudentShell (no dedicated staff UI yet)
 *   faculty  -> StudentShell (no dedicated faculty UI yet)
 *   student  -> StudentShell
 *   unknown  -> safe "Access restricted" shell (never privileged UI)
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App.tsx'
import * as adminApi from './services/adminApi.ts'
import type { DashboardSummary } from './types/admin.ts'

vi.mock('./services/adminApi.ts')
vi.mock('./services/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

const DASHBOARD_SUMMARY: DashboardSummary = {
  counts: {
    knowledge_sources: 0,
    documents: 0,
    faqs: 0,
    notices: 0,
    students: 0,
    student_results: 0,
    test_results: 0,
    attendance_records: 0,
  },
  recent_audit: [],
}

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
})

describe('App shell selection from the canonical /auth/me role', () => {
  it('shows AdminShell for the admin role', async () => {
    authState.role = 'admin'
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()
    // No /admin/me probe is used for role resolution.
    expect(adminApi.getAdminIdentity).not.toHaveBeenCalled()
  })

  it('shows the student shell for the student role', async () => {
    authState.role = 'student'
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('shows the student shell for the staff role (no privileged UI)', async () => {
    authState.role = 'staff'
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('shows the student shell for the faculty role (no privileged UI)', async () => {
    authState.role = 'faculty'
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
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

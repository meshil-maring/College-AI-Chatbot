/**
 * AdminShell component tests (Phase 6.19).
 *
 * Identity is read from the canonical AuthProvider state (resolved by
 * GET /auth/me); the shell NEVER probes GET /admin/me for role detection
 * and navigation is derived from the fail-closed adminNavigation model.
 * Security: no token material or internal identifiers may appear in the DOM.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminShell from './AdminShell.tsx'
import * as adminApi from '../../services/adminApi.ts'
import type { DashboardSummary } from '../../types/admin.ts'

vi.mock('../../services/adminApi.ts')
vi.mock('../chat/ChatShell.tsx', () => ({ default: () => <div>AI Assistant chat</div> }))

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
  user: {
    authenticated: true,
    user_id: 'u1',
    auth_user_id: 'a1',
    email: 'admin@test.com',
    role: 'admin' as const,
    institution_id: 'inst-1',
  },
  role: 'admin' as string | null,
  accessToken: 'test-token' as string | null,
  logout: vi.fn(),
}))

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

beforeEach(() => {
  authState.role = 'admin'
  authState.accessToken = 'test-token'
  authState.logout.mockReset()
  vi.mocked(adminApi.getAdminIdentity).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(DASHBOARD_SUMMARY)
})

describe('AdminShell', () => {
  it('renders the admin panel with the canonical identity from auth state', () => {
    render(<AdminShell />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByText('Signed in as admin@test.com')).toBeInTheDocument()
  })

  it('never probes GET /admin/me for role detection', () => {
    render(<AdminShell />)
    expect(adminApi.getAdminIdentity).not.toHaveBeenCalled()
  })

  it('renders the fail-closed admin navigation with real capabilities', () => {
    render(<AdminShell />)
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(nav).toBeInTheDocument()
    for (const label of [
      'Dashboard',
      'Student Approvals',
      'Students',
      'Attendance',
      'Results',
      'Test Results',
      'Notices',
      'Documents',
      'FAQs',
      'AI Assistant',
      'Profile',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('renders no admin navigation for non-admin roles (fail closed)', () => {
    authState.role = 'student'
    render(<AdminShell />)
    expect(screen.queryByRole('navigation', { name: 'Admin navigation' })).not.toBeInTheDocument()
  })

  it('marks the active view with aria-current', () => {
    render(<AdminShell />)
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
  })

  it('switches to the profile view showing only safe identity fields', async () => {
    const user = userEvent.setup()
    render(<AdminShell />)
    await user.click(screen.getByRole('button', { name: 'Profile' }))
    await waitFor(() => {
      expect(screen.getByText('Administrator identity')).toBeInTheDocument()
    })
    expect(screen.getByText('admin@test.com')).toBeInTheDocument()
    // Security: no token material or internal identifiers in the DOM.
    expect(screen.queryByText('test-token')).not.toBeInTheDocument()
    expect(screen.queryByText('u1')).not.toBeInTheDocument()
    expect(screen.queryByText('a1')).not.toBeInTheDocument()
    expect(screen.queryByText('inst-1')).not.toBeInTheDocument()
  })

  it('signs out via the shared logout', async () => {
    const user = userEvent.setup()
    render(<AdminShell />)
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })
})

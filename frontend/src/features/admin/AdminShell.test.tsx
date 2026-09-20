/**
 * AdminShell component tests.
 *
 * Phase 6.15.4 — identity is read from the canonical AuthProvider state
 * (resolved by GET /auth/me); the shell no longer probes GET /admin/me.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import AdminShell from './AdminShell.tsx'

vi.mock('../../services/adminApi.ts')
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: {
      authenticated: true,
      user_id: 'u1',
      auth_user_id: 'a1',
      email: 'admin@test.com',
      role: 'admin',
      institution_id: null,
    },
    role: 'admin',
    accessToken: 'test-token',
    logout: vi.fn(),
  }),
}))

describe('AdminShell', () => {
  it('renders the admin panel with the canonical identity from auth state', async () => {
    render(<AdminShell />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByText('admin@test.com')).toBeInTheDocument()
  })

  it('renders navigation items', () => {
    render(<AdminShell />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('FAQs')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('Notices')).toBeInTheDocument()
    expect(screen.getByText('Students')).toBeInTheDocument()
  })
})

/**
 * Phase Admin-4 — AdminShell component tests.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import AdminShell from './AdminShell.tsx'
import * as adminApi from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'test-token', user: null, logout: vi.fn() }),
}))

describe('AdminShell', () => {
  it('shows loading state while fetching admin identity', () => {
    vi.mocked(adminApi.getAdminIdentity).mockReturnValue(new Promise(() => {}))
    render(<AdminShell />)
    expect(screen.getByText('Loading admin…')).toBeInTheDocument()
  })

  it('shows admin panel after successful identity fetch', async () => {
    vi.mocked(adminApi.getAdminIdentity).mockResolvedValue({
      user_id: 'u1',
      auth_user_id: 'a1',
      email: 'admin@test.com',
      roles: ['admin'],
      is_admin: true,
    })
    render(<AdminShell />)
    await waitFor(() => {
      expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    })
    expect(screen.getByText('admin@test.com')).toBeInTheDocument()
  })

  it('shows access denied when identity fetch fails', async () => {
    vi.mocked(adminApi.getAdminIdentity).mockRejectedValue(new Error('Forbidden'))
    render(<AdminShell />)
    await waitFor(() => {
      expect(screen.getByText('Access denied')).toBeInTheDocument()
    })
  })

  it('renders navigation items', async () => {
    vi.mocked(adminApi.getAdminIdentity).mockResolvedValue({
      user_id: 'u1',
      auth_user_id: 'a1',
      email: 'admin@test.com',
      roles: ['admin'],
      is_admin: true,
    })
    render(<AdminShell />)
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('FAQs')).toBeInTheDocument()
      expect(screen.getByText('Documents')).toBeInTheDocument()
      expect(screen.getByText('Notices')).toBeInTheDocument()
      expect(screen.getByText('Students')).toBeInTheDocument()
    })
  })
})

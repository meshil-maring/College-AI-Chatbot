/**
 * Phase Admin-4 — App role gating tests.
 *
 * Verifies that admin users see AdminShell and student users see
 * ChatShell + AcademicsPanel.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createContext, useContext } from 'react'
import App from './App.tsx'
import * as adminApi from './services/adminApi.ts'

vi.mock('./services/adminApi.ts')

const AuthContext = createContext<{
  status: string
  user: unknown
  accessToken: string | null
  error: string | null
  login: ReturnType<typeof vi.fn>
  logout: ReturnType<typeof vi.fn>
}>({
  status: 'authenticated',
  user: null,
  accessToken: 'test-token',
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
})

vi.mock('./features/auth/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => {
    return <AuthContext.Provider value={{
      status: 'authenticated',
      user: null,
      accessToken: 'test-token',
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
    }}>{children}</AuthContext.Provider>
  },
  useAuth: () => useContext(AuthContext),
}))

describe('App role gating', () => {
  it('shows AdminShell for admin users', async () => {
    vi.mocked(adminApi.getAdminIdentity).mockResolvedValue({
      user_id: 'u1',
      auth_user_id: 'a1',
      email: 'admin@test.com',
      roles: ['admin'],
      is_admin: true,
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    })
  })

  it('shows My Academics for student users (non-admin)', async () => {
    vi.mocked(adminApi.getAdminIdentity).mockRejectedValue(new Error('Forbidden'))
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('My Academics')).toBeInTheDocument()
    })
  })
})

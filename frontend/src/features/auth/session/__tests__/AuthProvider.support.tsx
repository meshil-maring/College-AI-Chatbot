import { render } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import * as authService from '../../../../services/auth/auth.ts'
import { resetSessionExpiredListeners } from '../../../../services/shared/sessionEvents.ts'
import type { CurrentUser } from '../../../../types/auth.ts'
import { AuthProvider, useAuth } from '../AuthProvider.tsx'
vi.mock('../../../../services/auth/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../../../services/auth/auth.ts')>('../../../../services/auth/auth.ts')
  return {
    ...actual,
    authenticate: vi.fn(),
    fetchCurrentUser: vi.fn(),
    revokeSession: vi.fn(),
    refreshSession: vi.fn(),
  }
})

export const ME_ADMIN: CurrentUser = {
  authenticated: true,
  user_id: 'u-admin',
  auth_user_id: 'a-admin',
  email: 'admin@test.com',
  role: 'admin',
  institution_id: null,
}

export const ME_STUDENT: CurrentUser = {
  authenticated: true,
  user_id: 'u-student',
  auth_user_id: 'a-student',
  email: null,
  role: 'student',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

/** Renders nothing but captures the live auth context value. */
export let captured: ReturnType<typeof useAuth> | null = null

export function Probe() {
  captured = useAuth()
  return null
}

export function renderProvider() {
  captured = null
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  vi.mocked(authService.authenticate).mockReset()
  vi.mocked(authService.fetchCurrentUser).mockReset()
  vi.mocked(authService.revokeSession).mockReset()
  vi.mocked(authService.refreshSession).mockReset()
  vi.mocked(authService.revokeSession).mockResolvedValue({ message: 'revoked' })
  resetSessionExpiredListeners()
})

export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((done, fail) => {
    resolve = done
    reject = fail
  })
  return { promise, resolve, reject }
}

export const renewedSession = {
  access_token: 'renewed-token',
  refresh_token: 'renewed-refresh',
  expires_in: 3600,
  message: 'Login successful.',
  user: { id: 'a-student', email: null },
}

/**
 * Phase 6.15.4 — AuthProvider tests.
 *
 * Covers the canonical identity/role bootstrap and the session lifecycle:
 *   - restore (refresh bootstrap) via GET /auth/me, including role loading
 *   - login bootstrap: token -> /auth/me -> canonical identity + role
 *   - session expiry: an AUTHENTICATED API 401 clears the session, removes
 *     the token, returns to login, and shows the safe expiry message
 *   - login 401 regression: invalid credentials are classified
 *     `invalid_credentials` and NEVER trigger session-expiry handling
 *   - logout: auth state clears and the token is removed
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { AuthProvider, ACCESS_TOKEN_STORAGE_KEY, useAuth } from './AuthProvider.tsx'
import * as authService from '../../services/auth.ts'
import { AuthError } from '../../services/auth.ts'
import {
  SESSION_EXPIRED_MESSAGE,
  notifySessionExpired,
  resetSessionExpiredListeners,
} from '../../services/sessionEvents.ts'
import type { CurrentUser } from '../../types/auth.ts'

vi.mock('../../services/auth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/auth.ts')>(
    '../../services/auth.ts',
  )
  return {
    ...actual,
    authenticate: vi.fn(),
    fetchCurrentUser: vi.fn(),
  }
})

const ME_ADMIN: CurrentUser = {
  authenticated: true,
  user_id: 'u-admin',
  auth_user_id: 'a-admin',
  email: 'admin@test.com',
  role: 'admin',
  institution_id: null,
}

const ME_STUDENT: CurrentUser = {
  authenticated: true,
  user_id: 'u-student',
  auth_user_id: 'a-student',
  email: null,
  role: 'student',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

/** Renders nothing but captures the live auth context value. */
let captured: ReturnType<typeof useAuth> | null = null
function Probe() {
  captured = useAuth()
  return null
}

function renderProvider() {
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
  resetSessionExpiredListeners()
})

describe('restore (refresh bootstrap)', () => {
  it('an authenticated user restores successfully with role from /auth/me', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()

    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })
    expect(captured?.role).toBe('student')
    expect(captured?.user).toEqual(ME_STUDENT)
    expect(captured?.accessToken).toBe('saved-token')
    expect(authService.fetchCurrentUser).toHaveBeenCalledWith('saved-token')
    // The token survives a successful restore.
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('saved-token')
  })

  it('resolves the admin role on restore', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_ADMIN)

    renderProvider()

    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })
    expect(captured?.role).toBe('admin')
  })

  it('with no stored token there is no API call and status is unauthenticated', async () => {
    renderProvider()

    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    expect(authService.fetchCurrentUser).not.toHaveBeenCalled()
    expect(captured?.role).toBe(null)
  })

  it('a session-invalid /auth/me response clears the stored token', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'expired-token')
    vi.mocked(authService.fetchCurrentUser).mockRejectedValue(
      new AuthError('session_invalid', 401, 'TOKEN_EXPIRED'),
    )

    renderProvider()

    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(captured?.role).toBeNull()
  })
})

describe('login bootstrap', () => {
  it('stores the token and loads the canonical identity + role after login', async () => {
    vi.mocked(authService.authenticate).mockResolvedValue({
      access_token: 'fresh-token',
      message: 'Login successful.',
      user: { id: 'a-student', email: null },
    })
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })

    await act(async () => {
      await captured?.login('REG2026001', 'secret123', 'GIT')
    })

    expect(captured?.status).toBe('authenticated')
    expect(captured?.role).toBe('student')
    expect(captured?.accessToken).toBe('fresh-token')
    expect(authService.fetchCurrentUser).toHaveBeenCalledWith('fresh-token')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('fresh-token')
  })

  it('a rejected login shows invalid_credentials and never stores the token', async () => {
    vi.mocked(authService.authenticate).mockRejectedValue(
      new AuthError('invalid_credentials', 401, 'INVALID_CREDENTIALS'),
    )

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })

    await act(async () => {
      await captured?.login('REG2026001', 'wrong', 'GIT')
    })

    expect(captured?.status).toBe('unauthenticated')
    expect(captured?.error).toBe(
      'Invalid login credentials. Please check your details and try again.',
    )
    expect(captured?.role).toBeNull()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })
})

describe('session expiry (authenticated API 401)', () => {
  it('clears the session, removes the token, and shows the safe message', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })

    act(() => {
      // Simulates any authenticated API client receiving 401 TOKEN_EXPIRED.
      notifySessionExpired()
    })

    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    expect(captured?.error).toBe(SESSION_EXPIRED_MESSAGE)
    expect(captured?.role).toBeNull()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    // No stray alert nodes were rendered by the provider itself.
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('an expiry notification while unauthenticated is a no-op', async () => {
    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })

    act(() => {
      notifySessionExpired()
    })

    expect(captured?.status).toBe('unauthenticated')
    // No expiry message is manufactured without a real session.
    expect(captured?.error).toBeNull()
  })
})

describe('logout', () => {
  it('clears auth state and removes the stored token', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_ADMIN)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })

    act(() => {
      captured?.logout()
    })

    expect(captured?.status).toBe('unauthenticated')
    expect(captured?.user).toBeNull()
    expect(captured?.role).toBeNull()
    expect(captured?.accessToken).toBeNull()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })
})

/**
 * Phase 6.15.7 — race-guard security tests.
 *
 * Meaningful NEW assurance beyond the lifecycle tests above:
 *   - a stale 401 naming a REPLACED token can never clear a freshly
 *     established session (token-scoped expiry);
 *   - a login/restore that settles AFTER a logout can never resurrect the
 *     session (generation guard);
 *   - another tab signing out clears this tab's session (no tab stays
 *     authenticated on its own);
 *   - another tab signing in adopts the new session only after server-side
 *     validation.
 */
describe('Phase 6.15.7 — race guards', () => {
  it('a stale 401 naming a replaced token is ignored after re-login', async () => {
    vi.mocked(authService.authenticate).mockResolvedValue({
      access_token: 'fresh-token',
      message: 'Login successful.',
      user: { id: 'a-student', email: null },
    })
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    await act(async () => {
      await captured?.login('REG2026001', 'secret123', 'GIT')
    })
    expect(captured?.status).toBe('authenticated')

    act(() => {
      // A late 401 from the PREVIOUS session (request A was still in flight
      // when the user signed in again) must not clear the new session.
      notifySessionExpired('stale-previous-token')
    })

    expect(captured?.status).toBe('authenticated')
    expect(captured?.accessToken).toBe('fresh-token')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('fresh-token')
  })

  it('a 401 naming the CURRENT token still expires the session', async () => {
    vi.mocked(authService.authenticate).mockResolvedValue({
      access_token: 'current-token',
      message: 'Login successful.',
      user: { id: 'a-student', email: null },
    })
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    await act(async () => {
      await captured?.login('REG2026001', 'secret123', 'GIT')
    })

    act(() => {
      notifySessionExpired('current-token')
    })

    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    expect(captured?.error).toBe(SESSION_EXPIRED_MESSAGE)
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('a login that settles after logout cannot restore the session', async () => {
    let resolveAuth!: (value: {
      access_token: string
      message: string
      user: { id: string; email: string | null }
    }) => void
    vi.mocked(authService.authenticate).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveAuth = resolve
        }),
    )
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })

    let loginPromise: Promise<void> | undefined
    act(() => {
      loginPromise = captured?.login('REG2026001', 'secret123', 'GIT')
    })
    expect(captured?.status).toBe('authenticating')

    // The user signs out while the login is still in flight.
    act(() => {
      captured?.logout()
    })
    expect(captured?.status).toBe('unauthenticated')

    // The login response finally arrives — it must be discarded entirely.
    // fetchCurrentUser resolves normally (microtask); only `authenticate` is
    // manually released here.
    await act(async () => {
      resolveAuth({ access_token: 'late-token', message: 'Login successful.', user: { id: 'a-student', email: null } })
      await loginPromise
    })

    expect(captured?.status).toBe('unauthenticated')
    expect(captured?.accessToken).toBeNull()
    expect(captured?.role).toBeNull()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('another tab signing out clears this tab (cross-tab consistency)', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)

    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })

    // Tab B removes the token; the `storage` event fires in this tab (A).
    act(() => {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: ACCESS_TOKEN_STORAGE_KEY,
          storageArea: window.localStorage,
          newValue: null,
        }),
      )
    })

    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    expect(captured?.role).toBeNull()
  })

  it('another tab signing in adopts the session only after /auth/me validation', async () => {
    renderProvider()
    await waitFor(() => {
      expect(captured?.status).toBe('unauthenticated')
    })
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_ADMIN)

    act(() => {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'other-tab-token')
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: ACCESS_TOKEN_STORAGE_KEY,
          storageArea: window.localStorage,
          newValue: 'other-tab-token',
        }),
      )
    })

    await waitFor(() => {
      expect(captured?.status).toBe('authenticated')
    })
    expect(captured?.role).toBe('admin')
    expect(authService.fetchCurrentUser).toHaveBeenCalledWith('other-tab-token')
  })
})


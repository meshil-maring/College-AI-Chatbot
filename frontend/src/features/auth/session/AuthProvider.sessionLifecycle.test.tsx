import './__tests__/AuthProvider.support.tsx'
import { ME_ADMIN, ME_STUDENT, captured, renderProvider } from './__tests__/AuthProvider.support.tsx'
import { act, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import * as authService from '../../../services/auth/auth.ts'
import { AuthError } from '../../../services/auth/auth.ts'
import { SESSION_EXPIRED_MESSAGE, notifySessionExpired } from '../../../services/shared/sessionEvents.ts'
import { ACCESS_TOKEN_STORAGE_KEY } from './AuthProvider.tsx'
describe('navigation cache session lifetime', () => {
  const cachedKey = ['admin', 'academic-setup', 'saved-token']

  async function restoreAndCache() {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_ADMIN)
    renderProvider()
    await waitFor(() => expect(captured?.status).toBe('authenticated'))
    await queryClient.fetchQuery({
      queryKey: cachedKey,
      queryFn: async () => 'private academic records',
      ...NAVIGATION_QUERY_POLICY,
    })
    expect(queryClient.getQueryData(cachedKey)).toBe('private academic records')
  }

  it('keeps cached data when a late expiry notification names another session', async () => {
    await restoreAndCache()
    act(() => notifySessionExpired('retired-token'))
    expect(captured?.status).toBe('authenticated')
    expect(queryClient.getQueryData(cachedKey)).toBe('private academic records')
  })
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
    vi.mocked(authService.fetchCurrentUser).mockRejectedValue(new AuthError('session_invalid', 401, 'TOKEN_EXPIRED'))

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
      refresh_token: 'fresh-refresh-token',
      expires_in: 3600,
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
      'Invalid login credentials. Please check your details and try again. For help with account approval or access, contact your administrator.',
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

import './__tests__/AuthProvider.support.tsx'
import { ME_ADMIN, ME_STUDENT, captured, renderProvider } from './__tests__/AuthProvider.support.tsx'
import { act, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as authService from '../../../services/auth/auth.ts'
import { SESSION_EXPIRED_MESSAGE, notifySessionExpired } from '../../../services/shared/sessionEvents.ts'
import { ACCESS_TOKEN_STORAGE_KEY } from './AuthProvider.tsx'

describe('Phase 6.15.7 — race guards', () => {
  it('a stale 401 naming a replaced token is ignored after re-login', async () => {
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
      refresh_token: 'current-refresh-token',
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
      refresh_token: string
      expires_in: number
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
      resolveAuth({
        access_token: 'late-token',
        refresh_token: 'late-refresh',
        expires_in: 3600,
        message: 'Login successful.',
        user: { id: 'a-student', email: null },
      })
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

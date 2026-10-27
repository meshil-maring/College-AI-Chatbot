import './__tests__/AuthProvider.support.tsx'
import {
  ME_ADMIN,
  ME_STUDENT,
  Probe,
  captured,
  deferred,
  renderProvider,
  renewedSession,
} from './__tests__/AuthProvider.support.tsx'
import { act, render, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import * as authService from '../../../services/auth/auth.ts'
import { AuthError } from '../../../services/auth/auth.ts'
import { notifySessionExpired } from '../../../services/shared/sessionEvents.ts'
import type { CurrentUser, LoginResponse } from '../../../types/auth.ts'
import { ACCESS_TOKEN_STORAGE_KEY, AuthProvider, REFRESH_TOKEN_STORAGE_KEY } from './AuthProvider.tsx'
describe('session renewal race regressions', () => {
  it('proactively rotates and persists provider tokens without losing the authenticated identity', async () => {
    vi.useFakeTimers()
    try {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'saved-refresh')
      window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 120_000))
      vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)
      vi.mocked(authService.refreshSession).mockResolvedValue(renewedSession)
      await act(async () => {
        renderProvider()
      })
      expect(captured?.status).toBe('authenticated')
      const generation = captured?.sessionGeneration
      expect(generation).toEqual(expect.any(Number))
      expect(authService.refreshSession).not.toHaveBeenCalled()

      await act(async () => {
        await vi.advanceTimersByTimeAsync(60_000)
      })

      expect(authService.refreshSession).toHaveBeenCalledExactlyOnceWith('saved-refresh')
      expect(authService.fetchCurrentUser).toHaveBeenLastCalledWith('renewed-token')
      expect(captured?.status).toBe('authenticated')
      expect(captured?.user).toEqual(ME_STUDENT)
      expect(captured?.accessToken).toBe('renewed-token')
      expect(captured?.sessionGeneration).toBe(generation)
      expect(captured?.error).toBeNull()
      expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('renewed-token')
      expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('renewed-refresh')
      expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBe(String(Date.now() + 3600_000))
      await act(async () => {
        await captured!.logout()
      })
    } finally {
      vi.useRealTimers()
    }
  })

  it.each([
    new AuthError('account_inactive', 403, 'ACCOUNT_INACTIVE'),
    new AuthError('session_invalid', 401, 'TOKEN_EXPIRED'),
  ])('ignores stale cross-tab validation failure $code after a newer login', async (error) => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)
    renderProvider()
    await waitFor(() => expect(captured?.status).toBe('authenticated'))
    const olderValidation = deferred<CurrentUser>()
    vi.mocked(authService.fetchCurrentUser).mockReturnValueOnce(olderValidation.promise)
    act(() => {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'other-tab-token')
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: ACCESS_TOKEN_STORAGE_KEY,
          storageArea: window.localStorage,
        }),
      )
    })
    expect(captured?.status).toBe('restoring')
    vi.mocked(authService.authenticate).mockResolvedValue(renewedSession)
    vi.mocked(authService.fetchCurrentUser).mockResolvedValueOnce(ME_ADMIN)
    await act(async () => {
      await captured!.login('admin@example.test', 'test-password')
    })
    const expiryAfterLogin = window.localStorage.getItem('college-ai-chatbot.session-expires-at')
    await act(async () => {
      olderValidation.reject(error)
      await olderValidation.promise.catch(() => {})
    })

    expect(captured?.status).toBe('authenticated')
    expect(captured?.user).toEqual(ME_ADMIN)
    expect(captured?.role).toBe('admin')
    expect(captured?.accessToken).toBe('renewed-token')
    expect(captured?.error).toBeNull()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('renewed-token')
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('renewed-refresh')
    expect(window.localStorage.getItem('college-ai-chatbot.session-expires-at')).toBe(expiryAfterLogin)
  })

  it('renews an expired saved session once under StrictMode', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'expired-token')
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'saved-refresh')
    vi.mocked(authService.fetchCurrentUser)
      .mockRejectedValueOnce(new AuthError('session_invalid', 401, 'TOKEN_EXPIRED'))
      .mockResolvedValue(ME_STUDENT)
    vi.mocked(authService.refreshSession).mockResolvedValue(renewedSession)
    render(
      <StrictMode>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </StrictMode>,
    )
    await waitFor(() => expect(captured?.status).toBe('authenticated'))
    expect(authService.refreshSession).toHaveBeenCalledTimes(1)
    expect(captured?.accessToken).toBe('renewed-token')
  })

  it('does not persist a restored renewal that finishes after logout', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'expired-token')
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'saved-refresh')
    const pending = deferred<LoginResponse>()
    vi.mocked(authService.fetchCurrentUser)
      .mockRejectedValueOnce(new AuthError('session_invalid', 401, 'TOKEN_EXPIRED'))
      .mockResolvedValue(ME_STUDENT)
    vi.mocked(authService.refreshSession).mockReturnValue(pending.promise)
    renderProvider()
    await waitFor(() => expect(authService.refreshSession).toHaveBeenCalled())
    await act(async () => {
      await captured?.logout()
    })
    await act(async () => {
      pending.resolve(renewedSession)
      await pending.promise
    })
    expect(captured?.status).toBe('unauthenticated')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('keeps the newer login when an older login finishes later', async () => {
    const older = deferred<LoginResponse>()
    vi.mocked(authService.authenticate).mockReturnValueOnce(older.promise).mockResolvedValueOnce(renewedSession)
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)
    renderProvider()
    await waitFor(() => expect(captured?.status).toBe('unauthenticated'))
    let first!: Promise<void>
    act(() => {
      first = captured!.login('first@example.com', 'test-password')
    })
    await act(async () => {
      await captured!.login('second@example.com', 'test-password')
    })
    await act(async () => {
      older.resolve({ ...renewedSession, access_token: 'older-token' })
      await first
    })
    expect(captured?.accessToken).toBe('renewed-token')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('renewed-token')
  })

  it('does not clear a newer session when an old background renewal fails', async () => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'saved-token')
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'saved-refresh')
    window.localStorage.setItem('college-ai-chatbot.session-expires-at', String(Date.now() + 60_100))
    const pending = deferred<LoginResponse>()
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STUDENT)
    vi.mocked(authService.refreshSession).mockReturnValue(pending.promise)
    renderProvider()
    await waitFor(() => expect(authService.refreshSession).toHaveBeenCalled())
    vi.mocked(authService.authenticate).mockResolvedValue(renewedSession)
    await act(async () => {
      await captured!.login('new@example.com', 'test-password')
    })
    await act(async () => {
      pending.reject(new AuthError('session_invalid', 401, 'INVALID_TOKEN'))
      await pending.promise.catch(() => {})
    })
    expect(captured?.accessToken).toBe('renewed-token')
    expect(captured?.status).toBe('authenticated')
    expect(captured?.error).toBeNull()
  })
})

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

  it('removes retained data when signing out', async () => {
    await restoreAndCache()
    await act(async () => {
      await captured?.logout()
    })
    expect(captured?.status).toBe('unauthenticated')
    expect(queryClient.getQueryData(cachedKey)).toBeUndefined()
  })

  it('removes retained data when the current session expires', async () => {
    await restoreAndCache()
    act(() => notifySessionExpired('saved-token'))
    await waitFor(() => expect(captured?.status).toBe('unauthenticated'))
    expect(queryClient.getQueryData(cachedKey)).toBeUndefined()
  })

  it('clears retained data before adopting a session from another tab', async () => {
    await restoreAndCache()
    let resolve!: (user: CurrentUser) => void
    vi.mocked(authService.fetchCurrentUser).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'replacement-token')
    act(() =>
      window.dispatchEvent(
        new StorageEvent('storage', { key: ACCESS_TOKEN_STORAGE_KEY, storageArea: window.localStorage }),
      ),
    )
    expect(captured?.status).toBe('restoring')
    expect(queryClient.getQueryData(cachedKey)).toBeUndefined()
    await act(async () => resolve(ME_STUDENT))
    await waitFor(() => expect(captured?.accessToken).toBe('replacement-token'))
    expect(captured?.user).toEqual(ME_STUDENT)
  })
})

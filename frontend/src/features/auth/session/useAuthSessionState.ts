import { useCallback, useRef, useState } from 'react'
import { clearNavigationQueryCache } from '../../../lib/queryClient.ts'
import type { CurrentUser } from '../../../types/auth.ts'
import { type AuthStatus } from './context.ts'
import { clearStoredProviderSession } from './storage.ts'
export function useAuthSessionState() {
  const [status, setStatus] = useState<AuthStatus>('restoring')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  /**
   * Phase 6.15.7 — race guards.
   *
   * `sessionTokenRef` mirrors the token held in state so an incoming 401 can be
   * matched against the session it belongs to, and `sessionGenerationRef`
   * counts session invalidations so an async login/restore that settles AFTER a
   * logout, a session expiry, or a newer login is discarded instead of
   * restoring state that no longer applies.
   *
   * Both refs are written SYNCHRONOUSLY wherever the session changes, so a
   * stale response is detected even if React has not re-rendered yet.
   */
  const sessionTokenRef = useRef<string | null>(null)
  const sessionGenerationRef = useRef(0)
  const restoreStartedRef = useRef(false)

  /** Commit (or clear) the session token in state AND in the race-guard ref. */
  const setSessionToken = useCallback((token: string | null): void => {
    if (sessionTokenRef.current !== token) clearNavigationQueryCache()
    sessionTokenRef.current = token
    setAccessToken(token)
  }, [])

  /**
   * Drop the whole local session. Bumping the generation invalidates any
   * in-flight login/restore result, so a superseded operation can never restore
   * a session that has already been signed out. `message` is always a
   * user-safe string (null for a deliberate sign-out).
   */
  const clearSession = useCallback((message: string | null): void => {
    sessionGenerationRef.current += 1
    clearNavigationQueryCache()
    sessionTokenRef.current = null
    clearStoredProviderSession()
    setUser(null)
    setAccessToken(null)
    setError(message)
  }, [])
  return {
    status,
    setStatus,
    user,
    setUser,
    accessToken,
    setAccessToken,
    error,
    setError,
    sessionTokenRef,
    sessionGenerationRef,
    restoreStartedRef,
    setSessionToken,
    clearSession,
  }
}
export type AuthSessionState = ReturnType<typeof useAuthSessionState>

import { useCallback, useEffect } from 'react'
import { AuthError, authErrorMessage, fetchCurrentUser, refreshSession } from '../../../services/auth/auth.ts'
import { SESSION_EXPIRED_MESSAGE, onSessionExpired } from '../../../services/shared/sessionEvents.ts'
import {
  ACCESS_TOKEN_STORAGE_KEY,
  readStoredExpiry,
  readStoredRefreshToken,
  readStoredToken,
  storeProviderSession,
} from './storage.ts'
import type { AuthSessionState } from './useAuthSessionState.ts'
export function useSessionLifecycle(session: AuthSessionState) {
  const {
    status,
    setStatus,
    setUser,
    accessToken,
    setError,
    sessionTokenRef,
    sessionGenerationRef,
    setSessionToken,
    clearSession,
  } = session

  /**
   * Phase 6.15.4 — session-expiry handling for AUTHENTICATED requests.
   *
   * Any API client that receives a 401 on a request carrying the bearer token
   * publishes `notifySessionExpired(token)`; this handler clears the saved
   * session and returns the user to login with a safe, fixed message. It never
   * fires for login failures — those are classified as `invalid_credentials` by
   * the auth service and are not published on the session-expiry channel. A
   * stale notification arriving after logout is a no-op (already
   * unauthenticated, nothing to clear — the message is not shown for a
   * deliberate sign-out).
   *
   * Phase 6.15.7 — the notification names the token the failed request carried.
   * A notification for a token this provider no longer holds belongs to an
   * already-replaced session (for example: request A 401s while the user has
   * already signed in again and now holds a newer token) and is IGNORED, so a
   * stale 401 can never clear a freshly established session. A notification
   * without a token (a caller that cannot name it) keeps the previous
   * behavior: it applies to the current session.
   */
  const handleSessionExpired = useCallback(
    (expiredToken: string | null): void => {
      const currentToken = sessionTokenRef.current
      if (expiredToken !== null && currentToken !== null && expiredToken !== currentToken) {
        return
      }
      setStatus((currentStatus) => {
        if (currentStatus !== 'authenticated') return currentStatus
        clearSession(SESSION_EXPIRED_MESSAGE)
        return 'unauthenticated'
      })
    },
    [clearSession],
  )

  useEffect(() => {
    const unsubscribe = onSessionExpired(handleSessionExpired)
    return () => {
      unsubscribe()
    }
  }, [handleSessionExpired])

  useEffect(() => {
    if (status !== 'authenticated' || accessToken === null) return
    const refreshToken = readStoredRefreshToken()
    const expiresAt = readStoredExpiry()
    if (refreshToken === null || expiresAt === null) return

    const tokenAtStart = accessToken
    const generationAtStart = sessionGenerationRef.current
    let retryTimer: number | undefined
    const renew = async (): Promise<void> => {
      try {
        const refreshed = await refreshSession(refreshToken)
        const me = await fetchCurrentUser(refreshed.access_token)
        if (
          sessionGenerationRef.current !== generationAtStart ||
          sessionTokenRef.current !== tokenAtStart ||
          readStoredToken() !== tokenAtStart
        ) {
          return
        }
        storeProviderSession(refreshed.access_token, refreshed.refresh_token, refreshed.expires_in)
        setSessionToken(refreshed.access_token)
        setUser(me)
        setError(null)
      } catch (refreshError) {
        if (
          sessionGenerationRef.current !== generationAtStart ||
          sessionTokenRef.current !== tokenAtStart ||
          readStoredToken() !== tokenAtStart
        )
          return
        if (refreshError instanceof AuthError && refreshError.kind === 'network' && Date.now() < expiresAt) {
          retryTimer = window.setTimeout(() => void renew(), Math.min(10_000, Math.max(1, expiresAt - Date.now())))
          return
        }
        clearSession(
          refreshError instanceof AuthError && refreshError.kind === 'account_inactive'
            ? authErrorMessage(refreshError)
            : SESSION_EXPIRED_MESSAGE,
        )
        setStatus('unauthenticated')
      }
    }

    const timer = window.setTimeout(() => void renew(), Math.max(0, expiresAt - Date.now() - 60_000))
    return () => {
      window.clearTimeout(timer)
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
    }
  }, [accessToken, status, clearSession, setSessionToken])

  /**
   * Phase 6.15.7 — cross-tab consistency.
   *
   * Every tab of this origin shares the same saved token key, so a `storage`
   * event means another tab changed the session: it removed the token
   * (signed out / session expired there) or replaced it (signed in as a
   * possibly different account). Applying it here keeps no tab authenticated
   * on its own: a removed token clears this tab's session, a replaced token
   * re-validates through /auth/me and adopts the new identity. A notification
   * for THIS tab's own write never fires (the `storage` event only fires in
   * OTHER tabs), so there is no self-trigger loop.
   */
  useEffect(() => {
    const onStorage = (event: StorageEvent): void => {
      if (event.storageArea !== window.localStorage) return
      if (event.key !== null && event.key !== ACCESS_TOKEN_STORAGE_KEY) return
      const nextToken = readStoredToken()
      if (nextToken === sessionTokenRef.current) return
      if (nextToken === null) {
        // Another tab signed out (or its session expired): this tab must not
        // stay authenticated on its own.
        clearSession(SESSION_EXPIRED_MESSAGE)
        setStatus('unauthenticated')
        return
      }
      // Another tab signed in (possibly as a different account): adopt the
      // new session after server-side validation so role/identity stay
      // authoritative. Bumping the generation discards any in-flight
      // login/restore result for the previous session.
      sessionGenerationRef.current += 1
      const generationAtStart = sessionGenerationRef.current
      setSessionToken(nextToken)
      setStatus('restoring')
      void fetchCurrentUser(nextToken)
        .then((me) => {
          if (sessionGenerationRef.current !== generationAtStart) return
          if (readStoredToken() !== nextToken) return
          setUser(me)
          setSessionToken(nextToken)
          setError(null)
          setStatus('authenticated')
        })
        .catch((err) => {
          if (sessionGenerationRef.current !== generationAtStart) return
          if (readStoredToken() !== nextToken) return
          // The adopted token is not accepted: drop it so this tab does not
          // hold a dead session.
          clearSession(
            err instanceof AuthError && err.kind === 'account_inactive'
              ? authErrorMessage(err)
              : SESSION_EXPIRED_MESSAGE,
          )
          setStatus('unauthenticated')
        })
    }
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener('storage', onStorage)
    }
  }, [clearSession, setSessionToken])
}

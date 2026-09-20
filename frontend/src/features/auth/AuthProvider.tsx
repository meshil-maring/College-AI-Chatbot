/**
 * Phase 5.4 — Authentication state boundary.
 *
 * A small React context provider that owns the frontend authentication state:
 *   status      — restoring / unauthenticated / authenticating / authenticated
 *   user        — current application user (from GET /api/v1/auth/me)
 *   accessToken — the opaque Supabase JWT supplied to API clients in later phases
 *   login()     — backend password login + identity bootstrap
 *   logout()    — clears local auth state only: the backend authentication is
 *                 stateless JWT and exposes no logout/revocation endpoint,
 *                 so there is nothing to call.
 *
 * Persistence: the access token is the only credential-like value stored
 * (localStorage). The password is never stored. On mount the saved token is
 * re-validated through GET /api/v1/auth/me; a rejected token is cleared and a
 * network failure keeps it while surfacing a controlled error.
 *
 * Session/conversation bootstrap is intentionally NOT part of this phase: the
 * backend creates session/conversation identifiers only inside
 * POST /api/v1/generation/chat. No frontend UUID is fabricated.
 *
 * Phase 6.15.7 — production-hardening of the session lifecycle (no architecture
 * change; same token, same endpoints, same localStorage tradeoff):
 *   * stale async results are discarded — a login/restore that settles AFTER a
 *     logout, a session expiry, or a newer login can never resurrect (or
 *     overwrite) the current authentication state;
 *   * session-expiry notifications are TOKEN-SCOPED — a 401 reported by a
 *     request that carried an already-replaced token is ignored, so a late
 *     response cannot clear a freshly established session;
 *   * cross-tab consistency — the same saved token is shared by every tab of
 *     this origin, so a `storage` event (another tab signing out, or signing in
 *     as another account) is applied here as well instead of leaving this tab
 *     authenticated on its own.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AuthError, authErrorMessage, authenticate as authenticateRequest, fetchCurrentUser } from '../../services/auth.ts'
import { SESSION_EXPIRED_MESSAGE, onSessionExpired } from '../../services/sessionEvents.ts'
import type { CurrentUser } from '../../types/auth.ts'

/** localStorage key for the saved access token (opaque, never a password). */
export const ACCESS_TOKEN_STORAGE_KEY: string = 'college-ai-chatbot.access-token'

export type AuthStatus = 'restoring' | 'unauthenticated' | 'authenticating' | 'authenticated'

export interface AuthContextValue {
  readonly status: AuthStatus
  readonly user: CurrentUser | null
  /**
   * Phase 6.15.4 — SERVER-authoritative canonical role from /auth/me
   * (`user.role`). Never derived client-side; `null` = no supported role.
   */
  readonly role: CurrentUser['role']
  readonly accessToken: string | null
  /** User-safe error message from the last failed operation (never secrets). */
  readonly error: string | null
  /**
   * Sign in with a unified identifier (email / register number / university
   * roll number) — Phase 6.15.3. Email keeps the existing POST /auth/login
   * contract; academic identifiers go to POST /auth/student/login with the
   * institution code (required by the backend contract). The service layer
   * (`authenticate`) owns the routing decision.
   */
  readonly login: (
    identifier: string,
    password: string,
    institutionCode?: string,
  ) => Promise<void>
  readonly logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

function storeToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    } else {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    }
  } catch {
    // Storage unavailable (e.g. private browsing): the session stays in memory.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
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

  /** Commit (or clear) the session token in state AND in the race-guard ref. */
  const setSessionToken = useCallback((token: string | null): void => {
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
    sessionTokenRef.current = null
    storeToken(null)
    setUser(null)
    setAccessToken(null)
    setError(message)
  }, [])

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

  /** Re-validate any saved token against /auth/me and rebuild the session. */
  const restore = useCallback(async (): Promise<void> => {
    const token = readStoredToken()
    if (token === null) {
      setStatus('unauthenticated')
      setUser(null)
      setSessionToken(null)
      setError(null)
      return
    }
    const generationAtStart = sessionGenerationRef.current
    setStatus('restoring')
    try {
      const me = await fetchCurrentUser(token)
      // A logout/expiry/newer-login that settled while the request was
      // in-flight invalidates this result — never resurrect a superseded
      // session.
      if (sessionGenerationRef.current !== generationAtStart) return
      // Another tab may have replaced the saved token meanwhile; only adopt
      // this result when the saved token still matches what was validated.
      if (readStoredToken() !== token) return
      setUser(me)
      setSessionToken(token)
      setError(null)
      setStatus('authenticated')
    } catch (err) {
      if (sessionGenerationRef.current !== generationAtStart) return
      if (readStoredToken() !== token) return
      if (err instanceof AuthError && err.kind === 'session_invalid') {
        // The token is no longer accepted: discard the saved session.
        clearSession(null)
        setStatus('unauthenticated')
      } else {
        // Network failure: the token may still be valid, so keep it and
        // surface a controlled error. Any other failure discards it.
        setUser(null)
        const keep = err instanceof AuthError && err.kind === 'network'
        setSessionToken(keep ? token : null)
        storeToken(keep ? token : null)
        setError(err instanceof AuthError ? authErrorMessage(err) : 'Something went wrong during authentication. Please try again.')
        setStatus('unauthenticated')
      }
    }
  }, [clearSession, setSessionToken])

  useEffect(() => {
    void restore()
  }, [restore])

  const login = useCallback(
    async (
      identifier: string,
      password: string,
      institutionCode?: string,
    ): Promise<void> => {
      const generationAtStart = sessionGenerationRef.current
      setStatus('authenticating')
      setError(null)
      try {
        // Routes to POST /auth/login (email) or POST /auth/student/login
        // (academic identifier + institution code) — Phase 6.15.3.
        const response = await authenticateRequest(identifier, password, institutionCode)
        // Bootstrap identity through /auth/me so the state holds the same
        // user shape whether restored or freshly signed in.
        const me = await fetchCurrentUser(response.access_token)
        // A logout/expiry/newer-login that settled while the login was
        // in-flight invalidates this result — never restore over it.
        if (sessionGenerationRef.current !== generationAtStart) return
        storeToken(response.access_token)
        setUser(me)
        setSessionToken(response.access_token)
        setError(null)
        setStatus('authenticated')
      } catch (err) {
        if (sessionGenerationRef.current !== generationAtStart) return
        setStatus('unauthenticated')
        setError(
          err instanceof AuthError
            ? authErrorMessage(err)
            : 'Something went wrong during authentication. Please try again.',
        )
      }
    },
    [setSessionToken],
  )

  const logout = useCallback((): void => {
    clearSession(null)
    setStatus('unauthenticated')
  }, [clearSession])

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
      sessionTokenRef.current = nextToken
      setAccessToken(nextToken)
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
        .catch(() => {
          if (sessionGenerationRef.current !== generationAtStart) return
          if (readStoredToken() !== nextToken) return
          // The adopted token is not accepted: drop it so this tab does not
          // hold a dead session.
          clearSession(SESSION_EXPIRED_MESSAGE)
          setStatus('unauthenticated')
        })
    }
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener('storage', onStorage)
    }
  }, [clearSession, setSessionToken])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      role: user?.role ?? null,
      accessToken,
      error,
      login,
      logout,
    }),
    [status, user, accessToken, error, login, logout],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
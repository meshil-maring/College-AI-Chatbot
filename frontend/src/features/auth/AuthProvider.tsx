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
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AuthError, authErrorMessage, fetchCurrentUser, login as loginRequest } from '../../services/auth.ts'
import type { CurrentUser } from '../../types/auth.ts'

/** localStorage key for the saved access token (opaque, never a password). */
export const ACCESS_TOKEN_STORAGE_KEY: string = 'college-ai-chatbot.access-token'

export type AuthStatus = 'restoring' | 'unauthenticated' | 'authenticating' | 'authenticated'

export interface AuthContextValue {
  readonly status: AuthStatus
  readonly user: CurrentUser | null
  readonly accessToken: string | null
  /** User-safe error message from the last failed operation (never secrets). */
  readonly error: string | null
  readonly login: (email: string, password: string) => Promise<void>
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

  /** Re-validate any saved token against /auth/me and rebuild the session. */
  const restore = useCallback(async (): Promise<void> => {
    const token = readStoredToken()
    if (token === null) {
      setStatus('unauthenticated')
      setUser(null)
      setAccessToken(null)
      setError(null)
      return
    }
    setStatus('restoring')
    try {
      const me = await fetchCurrentUser(token)
      setUser(me)
      setAccessToken(token)
      setError(null)
      setStatus('authenticated')
    } catch (err) {
      if (err instanceof AuthError && err.kind === 'session_invalid') {
        // The token is no longer accepted: discard the saved session.
        storeToken(null)
        setUser(null)
        setAccessToken(null)
        setError(null)
        setStatus('unauthenticated')
      } else {
        // Network failure: the token may still be valid, so keep it and
        // surface a controlled error. Any other failure discards it.
        setUser(null)
        setAccessToken(err instanceof AuthError && err.kind === 'network' ? token : null)
        storeToken(err instanceof AuthError && err.kind === 'network' ? token : null)
        setError(err instanceof AuthError ? authErrorMessage(err) : 'Something went wrong during authentication. Please try again.')
        setStatus('unauthenticated')
      }
    }
  }, [])

  useEffect(() => {
    void restore()
  }, [restore])

  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      setStatus('authenticating')
      setError(null)
      try {
        const response = await loginRequest({ email, password })
        // Bootstrap identity through /auth/me so the state holds the same
        // user shape whether restored or freshly signed in.
        const me = await fetchCurrentUser(response.access_token)
        storeToken(response.access_token)
        setUser(me)
        setAccessToken(response.access_token)
        setError(null)
        setStatus('authenticated')
      } catch (err) {
        setStatus('unauthenticated')
        setError(
          err instanceof AuthError
            ? authErrorMessage(err)
            : 'Something went wrong during authentication. Please try again.',
        )
      }
    },
    [],
  )

  const logout = useCallback((): void => {
    storeToken(null)
    setUser(null)
    setAccessToken(null)
    setError(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
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
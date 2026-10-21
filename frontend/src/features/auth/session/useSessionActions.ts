import { useCallback } from 'react'
import {
  AuthError,
  authErrorMessage,
  authenticate as authenticateRequest,
  fetchCurrentUser,
  revokeSession,
} from '../../../services/auth/auth.ts'
import { clearStoredProviderSession, storeProviderSession } from './storage.ts'
import type { AuthSessionState } from './useAuthSessionState.ts'
export function useSessionActions(session: AuthSessionState) {
  const { setStatus, setUser, setError, sessionTokenRef, sessionGenerationRef, setSessionToken, clearSession } = session

  const login = useCallback(
    async (identifier: string, password: string, institutionCode?: string): Promise<void> => {
      const generationAtStart = ++sessionGenerationRef.current
      setStatus('authenticating')
      setError(null)
      setUser(null)
      setSessionToken(null)
      clearStoredProviderSession()
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
        storeProviderSession(response.access_token, response.refresh_token, response.expires_in)
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

  const logout = useCallback(async (): Promise<void> => {
    const token = sessionTokenRef.current
    clearSession(null)
    const generationAtLogout = sessionGenerationRef.current
    setStatus('unauthenticated')
    if (token === null) return
    try {
      await revokeSession(token)
    } catch {
      if (sessionGenerationRef.current === generationAtLogout && sessionTokenRef.current === null) {
        setError(
          'You have been signed out on this device, but the authentication provider could not revoke the session.',
        )
      }
    }
  }, [clearSession])

  const logoutAll = useCallback(async (): Promise<void> => {
    const token = sessionTokenRef.current
    const generationAtStart = sessionGenerationRef.current
    if (token === null) {
      clearSession(null)
      setStatus('unauthenticated')
      return
    }
    try {
      await revokeSession(token, true)
      if (sessionGenerationRef.current !== generationAtStart || sessionTokenRef.current !== token) {
        return
      }
      clearSession(null)
      setStatus('unauthenticated')
    } catch {
      if (sessionGenerationRef.current !== generationAtStart || sessionTokenRef.current !== token) {
        return
      }
      clearSession(
        'You have been signed out on this device, but the authentication provider could not revoke all sessions.',
      )
      setStatus('unauthenticated')
    }
  }, [clearSession])
  return { login, logout, logoutAll }
}

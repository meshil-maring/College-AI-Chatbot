import { useCallback, useEffect } from 'react'
import { AuthError, authErrorMessage, fetchCurrentUser, refreshSession } from '../../../services/auth/auth.ts'
import { SESSION_EXPIRED_MESSAGE } from '../../../services/shared/sessionEvents.ts'
import type { CurrentUser } from '../../../types/auth.ts'
import { clearStoredProviderSession, readStoredRefreshToken, readStoredToken, storeProviderSession } from './storage.ts'
import type { AuthSessionState } from './useAuthSessionState.ts'
export function useSessionRestore(session: AuthSessionState) {
  const { setStatus, setUser, setError, sessionGenerationRef, restoreStartedRef, setSessionToken, clearSession } =
    session

  /** Re-validate any saved token against /auth/me and rebuild the session. */
  const restore = useCallback(async (): Promise<void> => {
    const token = readStoredToken()
    if (token === null) {
      clearStoredProviderSession()
      setStatus('unauthenticated')
      setUser(null)
      setSessionToken(null)
      setError(null)
      return
    }
    const generationAtStart = sessionGenerationRef.current
    const savedRefreshToken = readStoredRefreshToken()
    setStatus('restoring')
    try {
      let restoredToken = token
      let me: CurrentUser
      try {
        me = await fetchCurrentUser(token)
      } catch (restoreError) {
        if (
          !(restoreError instanceof AuthError) ||
          restoreError.kind !== 'session_invalid' ||
          savedRefreshToken === null
        ) {
          throw restoreError
        }
        const renewed = await refreshSession(savedRefreshToken)
        restoredToken = renewed.access_token
        me = await fetchCurrentUser(restoredToken)
        if (sessionGenerationRef.current !== generationAtStart || readStoredToken() !== token) return
        storeProviderSession(renewed.access_token, renewed.refresh_token, renewed.expires_in)
      }
      // A logout/expiry/newer-login that settled while the request was
      // in-flight invalidates this result — never resurrect a superseded
      // session.
      if (sessionGenerationRef.current !== generationAtStart) return
      // Another tab may have replaced the saved token meanwhile; only adopt
      // this result when the saved token still matches what was validated.
      if (readStoredToken() !== token && readStoredToken() !== restoredToken) return
      setUser(me)
      setSessionToken(restoredToken)
      setError(null)
      setStatus('authenticated')
    } catch (err) {
      if (sessionGenerationRef.current !== generationAtStart) return
      if (readStoredToken() !== token) return
      if (err instanceof AuthError && err.kind === 'session_invalid') {
        // The token is no longer accepted: discard the saved session.
        clearSession(SESSION_EXPIRED_MESSAGE)
        setStatus('unauthenticated')
      } else {
        // Network failure: the token may still be valid, so keep it and
        // surface a controlled error. Any other failure discards it.
        setUser(null)
        const keep = err instanceof AuthError && err.kind === 'network'
        setSessionToken(keep ? token : null)
        if (!keep) clearStoredProviderSession()
        setError(
          err instanceof AuthError
            ? authErrorMessage(err)
            : 'Something went wrong during authentication. Please try again.',
        )
        setStatus('unauthenticated')
      }
    }
  }, [clearSession, setSessionToken])

  useEffect(() => {
    // Do not rotate the same refresh token twice during StrictMode replay.
    if (restoreStartedRef.current) return
    restoreStartedRef.current = true
    void restore()
  }, [restore])
}

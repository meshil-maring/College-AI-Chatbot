import { useMemo, type ReactNode } from 'react'
import { AuthContext, type AuthContextValue } from './context.ts'
import { useAuthSessionState } from './useAuthSessionState.ts'
import { useSessionActions } from './useSessionActions.ts'
import { useSessionLifecycle } from './useSessionLifecycle.ts'
import { useSessionRestore } from './useSessionRestore.ts'
export { useAuth, type AuthContextValue, type AuthStatus } from './context.ts'
export { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from './storage.ts'
export function AuthProvider({ children }: { children: ReactNode }) {
  const session = useAuthSessionState()
  useSessionRestore(session)
  useSessionLifecycle(session)
  const { login, logout, logoutAll } = useSessionActions(session)
  const { status, user, accessToken, error } = session
  const sessionGeneration = session.sessionGenerationRef.current

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      role: user?.role ?? null,
      accessToken,
      sessionGeneration,
      error,
      login,
      logout,
      logoutAll,
    }),
    [status, user, accessToken, sessionGeneration, error, login, logout, logoutAll],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

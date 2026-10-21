import { createContext, useContext } from 'react'
import type { CurrentUser } from '../../../types/auth.ts'
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
  readonly login: (identifier: string, password: string, institutionCode?: string) => Promise<void>
  readonly logout: () => Promise<void>
  readonly logoutAll: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

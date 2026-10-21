import { type LoginAudience } from '../features/auth/login/LoginForm.tsx'
import { resolveFacultyRoute } from '../features/faculty/workspace/facultyRoutes.ts'

export function decodeInstitutionCode(value: string | undefined): string | null {
  if (value === undefined) return null
  try {
    const code = decodeURIComponent(value).trim().toUpperCase()
    return /^[A-Z0-9][A-Z0-9_-]{0,31}$/.test(code) ? code : null
  } catch {
    return null
  }
}

export function resolvePublicInstitutionCode(pathname: string): string | null | undefined {
  const match = pathname.match(/^\/public-chat(?:\/([^/]+))?\/?$/)
  if (match === null) return undefined
  return decodeInstitutionCode(match[1])
}

export type AppRoute =
  | { readonly kind: 'home' }
  | { readonly kind: 'login'; readonly audience: LoginAudience }
  | { readonly kind: 'reset-password' }
  | { readonly kind: 'super-admin' }
  | { readonly kind: 'faculty' }
  | { readonly kind: 'admin-invitation'; readonly token: string }
  | { readonly kind: 'super-admin-invitation'; readonly token: string }
  | { readonly kind: 'super-admin-register' }
  | { readonly kind: 'university-registration' }
  | { readonly kind: 'institution-entry' }
  | { readonly kind: 'institution'; readonly institutionCode: string }
  | { readonly kind: 'institution-ai'; readonly institutionCode: string }
  | { readonly kind: 'public-chat'; readonly institutionCode: string | null }
  | { readonly kind: 'not-found' }

/**
 * Extract the opaque invitation token from `/admin-invite/{token}`.
 *
 * The token is returned VERBATIM — it is a base64url credential, not an
 * identifier, so any case folding or re-encoding would corrupt it. Only the
 * obviously-malformed shapes (empty, wrong segment count, unsafe characters) are
 * rejected; every authorization decision is made by the server.
 */
export function resolveInvitationToken(pathname: string): string | null | undefined {
  const match = pathname.match(/^\/admin-invite\/([^/]+)\/?$/)
  if (match === null) return undefined
  let token: string
  try {
    token = decodeURIComponent(match[1])
  } catch {
    return null
  }
  // 32-256 chars of URL-safe base64, matching the backend's acceptance bounds.
  return /^[A-Za-z0-9_-]{32,256}$/.test(token) ? token : null
}

export function resolveAppRoute(pathname: string): AppRoute {
  if (resolveFacultyRoute(pathname)) return { kind: 'faculty' }
  const publicInstitutionCode = resolvePublicInstitutionCode(pathname)
  if (publicInstitutionCode !== undefined) {
    return { kind: 'public-chat', institutionCode: publicInstitutionCode }
  }
  // The invitation route is PUBLIC: the invited person has no account yet, so it
  // is resolved before any AuthProvider gate and never depends on session state.
  const invitationToken = resolveInvitationToken(pathname)
  if (invitationToken !== undefined) {
    return invitationToken === null ? { kind: 'not-found' } : { kind: 'admin-invitation', token: invitationToken }
  }
  const superAdminMatch = pathname.match(/^\/super-admin-invite\/([^/]+)\/?$/)
  if (superAdminMatch !== null) {
    let token: string | null = null
    try {
      token = decodeURIComponent(superAdminMatch[1])
    } catch {
      token = null
    }
    return token !== null && /^[A-Za-z0-9_-]{32,256}$/.test(token)
      ? { kind: 'super-admin-invitation', token }
      : { kind: 'not-found' }
  }
  if (/^\/register\/super-admin\/?$/.test(pathname)) return { kind: 'super-admin-register' }
  if (pathname === '/' || pathname === '') return { kind: 'home' }
  if (/^\/reset-password\/?$/.test(pathname)) return { kind: 'reset-password' }
  if (/^\/register\/university\/?$/.test(pathname)) return { kind: 'university-registration' }
  if (/^\/u\/?$/.test(pathname)) return { kind: 'institution-entry' }

  const institutionMatch = pathname.match(/^\/u\/([^/]+)(?:\/(ai))?\/?$/)
  if (institutionMatch !== null) {
    const institutionCode = decodeInstitutionCode(institutionMatch[1])
    if (institutionCode === null) return { kind: 'not-found' }
    return institutionMatch[2] === 'ai'
      ? { kind: 'institution-ai', institutionCode }
      : { kind: 'institution', institutionCode }
  }

  if (/^\/super-admin\/?$/.test(pathname)) return { kind: 'super-admin' }
  const loginMatch = pathname.match(/^\/login(?:\/(student|admin|staff|faculty))?\/?$/)
  if (loginMatch !== null) {
    return { kind: 'login', audience: (loginMatch[1] as LoginAudience | undefined) ?? 'general' }
  }
  return { kind: 'not-found' }
}

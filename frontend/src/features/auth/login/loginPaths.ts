import { isSignupType, signupPath } from '../registration/signupPaths.ts'

/**
 * Everyone signs in at one page. Students, faculty, staff and university
 * admins use the same form; after sign-in the server resolves the account's
 * role and the app opens the matching workspace. The URL never selects a role.
 */
export const LOGIN_PATH = '/login'

/** Shared sign-in page, optionally pre-filling the institution code for register/roll-number sign-in. */
export function loginPath(institutionCode?: string | null): string {
  const code = institutionCode?.trim()
  return code ? `${LOGIN_PATH}?institution=${encodeURIComponent(code)}` : LOGIN_PATH
}

/**
 * Map retired role-specific auth URLs to their current page so bookmarks,
 * emails and shared links keep working:
 * - `/login/<student|faculty|staff>?register=1` → `/signup/<type>` (institution kept)
 * - `/login/<student|faculty|staff|admin>` → `/login`, keeping other query values
 *
 * Returns null when the URL is already current.
 */
export function legacyAuthRedirect(pathname: string, search: string): string | null {
  const match = pathname.match(/^\/login\/(student|faculty|staff|admin)\/?$/)
  if (match === null) return null
  const params = new URLSearchParams(search)
  const wantsSignup = params.get('register') === '1'
  if (wantsSignup && isSignupType(match[1])) return signupPath(match[1], params.get('institution'))
  params.delete('register')
  const query = params.toString()
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH
}

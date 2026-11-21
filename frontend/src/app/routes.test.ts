import { describe, expect, it } from 'vitest'
import { legacyAuthRedirect, loginPath } from '../features/auth/login/loginPaths.ts'
import { signupPath } from '../features/auth/registration/signupPaths.ts'
import { resolveAppRoute } from './routes.ts'

describe('public student setup route', () => {
  it('resolves without requiring the invitation token in the path', () => {
    expect(resolveAppRoute('/student-setup')).toEqual({ kind: 'student-setup' })
    expect(resolveAppRoute('/student-setup/')).toEqual({ kind: 'student-setup' })
  })
})

describe('per-type signup routes', () => {
  it.each(['student', 'faculty', 'staff'] as const)('resolves /signup/%s to its own registration form', (type) => {
    expect(resolveAppRoute(`/signup/${type}`)).toEqual({ kind: 'signup', registrationType: type })
    expect(resolveAppRoute(`/signup/${type}/`)).toEqual({ kind: 'signup', registrationType: type })
  })

  it('does not offer public signup for privileged or unknown account types', () => {
    for (const path of ['/signup', '/signup/admin', '/signup/super_admin', '/signup/super-admin', '/signup/x']) {
      expect(resolveAppRoute(path)).toEqual({ kind: 'not-found' })
    }
  })

  it('builds signup links with an encoded institution code', () => {
    expect(signupPath('student')).toBe('/signup/student')
    expect(signupPath('faculty', ' GIT ')).toBe('/signup/faculty?institution=GIT')
    expect(signupPath('student', 'A&B')).toBe('/signup/student?institution=A%26B')
  })

  it('sends retired registration links to the matching signup page', () => {
    expect(legacyAuthRedirect('/login/student', '?institution=GIT&register=1')).toBe('/signup/student?institution=GIT')
    expect(legacyAuthRedirect('/login/staff', '?register=1')).toBe('/signup/staff')
  })

  it('sends retired role sign-in links to the one shared sign-in page', () => {
    expect(legacyAuthRedirect('/login/student', '?institution=GIT')).toBe('/login?institution=GIT')
    expect(legacyAuthRedirect('/login/faculty/', '')).toBe('/login')
    expect(legacyAuthRedirect('/login/admin', '?register=1')).toBe('/login')
    expect(legacyAuthRedirect('/login/admin', '?view=approvals&student-page=all')).toBe(
      '/login?view=approvals&student-page=all',
    )
    expect(legacyAuthRedirect('/login', '?institution=GIT')).toBeNull()
    expect(legacyAuthRedirect('/login/super_admin', '')).toBeNull()
  })

  it('builds the shared sign-in link with an encoded institution code', () => {
    expect(loginPath()).toBe('/login')
    expect(loginPath(' A&B ')).toBe('/login?institution=A%26B')
  })
})

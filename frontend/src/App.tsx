import { useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './features/auth/AuthProvider.tsx'
import LoginForm, { type LoginAudience } from './features/auth/LoginForm.tsx'
import ChangePasswordForm from './features/auth/ChangePasswordForm.tsx'
import AdminShell from './features/admin/AdminShell.tsx'
import StudentShell from './features/student/StudentShell.tsx'
import FacultyShell from './features/faculty/FacultyShell.tsx'
import StaffShell from './features/staff/StaffShell.tsx'
import { fetchDevAuthStatus } from './services/devAuth.ts'
import PublicChatPage, { PublicChatRouteError } from './features/publicChat/PublicChatPage.tsx'
import LandingPage from './features/landing/LandingPage.tsx'
import InstitutionEntryPage from './features/landing/InstitutionEntryPage.tsx'
import InstitutionGatewayPage from './features/landing/InstitutionGatewayPage.tsx'
import SuperAdminShell from './features/superAdmin/SuperAdminShell.tsx'
import AdminInvitationPage from './features/adminInvitation/AdminInvitationPage.tsx'
import UniversityRegistrationPage from './features/auth/UniversityRegistrationPage.tsx'

function decodeInstitutionCode(value: string | undefined): string | null {
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
  | { readonly kind: 'super-admin' }
  | { readonly kind: 'admin-invitation'; readonly token: string }
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
function resolveInvitationToken(pathname: string): string | null | undefined {
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
  const publicInstitutionCode = resolvePublicInstitutionCode(pathname)
  if (publicInstitutionCode !== undefined) {
    return { kind: 'public-chat', institutionCode: publicInstitutionCode }
  }
  // The invitation route is PUBLIC: the invited person has no account yet, so it
  // is resolved before any AuthProvider gate and never depends on session state.
  const invitationToken = resolveInvitationToken(pathname)
  if (invitationToken !== undefined) {
    return invitationToken === null
      ? { kind: 'not-found' }
      : { kind: 'admin-invitation', token: invitationToken }
  }
  if (pathname === '/' || pathname === '') return { kind: 'home' }
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

/** DEVELOPMENT / TESTING ONLY — collapsible "Change Password" panel. */
function DevChangePasswordPanel() {
  const [devTestModeEnabled, setDevTestModeEnabled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    void fetchDevAuthStatus().then((result) => {
      if (!cancelled) setDevTestModeEnabled(result.dev_test_mode)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!devTestModeEnabled) return null

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open ? (
        <div id="dev-change-password-panel" className="flex flex-col items-end gap-2">
          <ChangePasswordForm />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-xs text-slate-400 hover:text-slate-200 underline"
          >
            Close
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={open}
          aria-controls="dev-change-password-panel"
          className="rounded-lg border border-amber-600/60 bg-slate-800 px-3 py-2 text-xs font-semibold text-amber-400 shadow-lg hover:bg-slate-700"
        >
          Change Password (Dev/Test only)
        </button>
      )}
    </div>
  )
}

function RestoringShell() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
          <h1 className="text-4xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-4 text-lg text-slate-300">Restoring your session…</p>
        </div>
      </main>
    </div>
  )
}

/**
 * Phase 6.16 — Student experience shell composition.
 *
 * The pre-6.16 shell rendered `ChatShell` (+ the `AcademicsPanel` modal)
 * directly here. The coherent student navigation now lives in
 * `features/student/StudentShell.tsx`, which reuses the same `ChatShell` for
 * its assistant view.
 */

/**
 * Phase 6.18 — staff shell selection added; the selection model is
 * unchanged: the shell is selected from the SERVER-authoritative role
 * resolved by /auth/me (held in AuthProvider state). No /admin/me probe, no
 * inference from email/identifier/storage: the backend decides, the
 * frontend renders.
 *
 * Faculty -> FacultyShell (Phase 6.17; server-verified capabilities only).
 * Staff -> StaffShell (Phase 6.18; server-verified capabilities only:
 * the Phase 6.4 tenant-scoped approval queue + the existing ChatShell).
 *
 * Unknown/unsupported role (`null` or any value outside AuthRole) fails
 * SAFELY: no privileged UI — the user sees a controlled access message and
 * can sign out. A role is only ever privileged when it equals 'admin'.
 *
 * Phase 6.20 — role shells are additionally keyed on the canonical
 * identity, so a session replacement can never leave a previous role's (or a
 * previous tenant's) view state mounted. See `AuthenticatedShell`.
 */
function AuthenticatedShell() {
  const { user, role, logout } = useAuth()

  /**
   * Phase 6.20 — identity-scoped shell key.
   *
   * Shell selection happens per render, but React REUSES a component instance
   * when the element type and position are unchanged. Two authentication
   * replacements keep the same element type:
   *
   *   * the same role with a DIFFERENT account/tenant (admin A -> admin B),
   *     which is exactly the cross-tenant case the backend isolates;
   *   * any role change that React would otherwise reconcile in place.
   *
   * Keying the shell on the canonical identity (`role` + server-issued
   * `auth_user_id`, both from `/auth/me`) forces React to unmount the previous
   * shell and mount a fresh one, so in-shell view state (e.g. an open
   * "Documents" manager) and already-fetched role data can never survive an
   * authentication replacement. This is UX state hygiene only — every request
   * remains authorized server-side from the JWT.
   */
  const shellKey = `${role ?? 'unsupported'}:${user?.auth_user_id ?? user?.user_id ?? 'unknown'}`

  if (role === 'admin') {
    return <AdminShell key={shellKey} />
  }
  if (role === 'super_admin') {
    return <SuperAdminShell key={shellKey} />
  }
  if (role === 'faculty') {
    return <FacultyShell key={shellKey} />
  }
  if (role === 'staff') {
    return <StaffShell key={shellKey} />
  }
  if (role === 'student') {
    return <StudentShell key={shellKey} />
  }
  return <UnsupportedRoleShell key={shellKey} onSignOut={logout} />
}

function UnsupportedRoleShell({ onSignOut }: { onSignOut: () => void }) {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-2xl border border-amber-900/50 bg-amber-500/10 p-10 shadow-xl">
          <h1 className="text-2xl font-bold text-amber-300">Access restricted</h1>
          <p className="mt-4 text-slate-300">
            This account does not have an application role assigned. Please
            contact your institution administrator.
          </p>
          <button
            type="button"
            onClick={onSignOut}
            className="mt-6 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            Sign out
          </button>
        </div>
      </main>
    </div>
  )
}

function AuthGate({ audience = 'general' }: { audience?: LoginAudience }) {
  const { status } = useAuth()
  if (status === 'restoring') {
    return <RestoringShell />
  }
  if (status === 'authenticated') {
    return (
      <>
        <AuthenticatedShell />
        <DevChangePasswordPanel />
      </>
    )
  }
  return <LoginForm audience={audience} />
}

function RootGate() {
  const { status, error } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status === 'authenticated') {
    return (
      <>
        <AuthenticatedShell />
        <DevChangePasswordPanel />
      </>
    )
  }
  // A rejected/expired saved session still lands on the shared login form so
  // the established safe authentication error remains visible. Deliberate
  // sign-out (no error) returns to the public demo gateway.
  if (error !== null) return <LoginForm />
  return <LandingPage />
}

function SuperAdminGate() {
  const { status, role, logout } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status !== 'authenticated') return <LoginForm audience="super_admin" />
  if (role === 'super_admin') return <SuperAdminShell />
  return <UnsupportedRoleShell onSignOut={logout} />
}

function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
      <section className="max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-white">Page not found</h1>
        <p className="mt-3 text-sm text-slate-400">This demo route is not available.</p>
        <a href="/" className="mt-6 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-300">Return to College AI</a>
      </section>
    </main>
  )
}

function App() {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  useEffect(() => {
    const updatePathname = (): void => setPathname(window.location.pathname)
    window.addEventListener('popstate', updatePathname)
    return () => window.removeEventListener('popstate', updatePathname)
  }, [])
  const route = resolveAppRoute(pathname)
  if (route.kind === 'public-chat') {
    return route.institutionCode === null
      ? <PublicChatRouteError />
      : <PublicChatPage institutionCode={route.institutionCode} />
  }
  if (route.kind === 'institution-ai') return <PublicChatPage institutionCode={route.institutionCode} />
  if (route.kind === 'institution-entry') return <InstitutionEntryPage />
  if (route.kind === 'institution') return <InstitutionGatewayPage institutionCode={route.institutionCode} />
  if (route.kind === 'not-found') return <NotFoundPage />
  // Rendered outside <AuthProvider>: the invited person has no session yet.
  if (route.kind === 'admin-invitation') return <AdminInvitationPage token={route.token} />
  // Public onboarding request. The backend creates only a pending institution;
  // no usable admin access exists until the server-side approval workflow.
  if (route.kind === 'university-registration') return <UniversityRegistrationPage />
  return (
    <AuthProvider>
      {route.kind === 'home' ? <RootGate /> : null}
      {route.kind === 'login' ? <AuthGate audience={route.audience} /> : null}
      {route.kind === 'super-admin' ? <SuperAdminGate /> : null}
    </AuthProvider>
  )
}

export default App

import { useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './features/auth/AuthProvider.tsx'
import LoginForm from './features/auth/LoginForm.tsx'
import ChangePasswordForm from './features/auth/ChangePasswordForm.tsx'
import AdminShell from './features/admin/AdminShell.tsx'
import StudentShell from './features/student/StudentShell.tsx'
import FacultyShell from './features/faculty/FacultyShell.tsx'
import StaffShell from './features/staff/StaffShell.tsx'
import { fetchDevAuthStatus } from './services/devAuth.ts'

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
 * Phase 6.20 — the four shells are additionally keyed on the canonical
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

function AuthGate() {
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
  return <LoginForm />
}

function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}

export default App

/**
 * Phase Admin-4 / Phase 6.19 — Admin shell.
 *
 * The administrative application shell. Navigation (navigation model,
 * fail-closed role gating, per-view headings) is defined in
 * `adminNavigation.ts`, derived exclusively from the server-authoritative
 * role held in AuthProvider state (`/auth/me` -> `user.role`, Phase 6.15.4).
 * This shell does NOT probe GET /admin/me for identity or role: the canonical
 * identity comes from the same AuthProvider state, so one authenticated
 * request bootstraps everything. Authorization itself remains fully
 * backend-enforced: every admin API request still carries the bearer token
 * and /admin/* endpoints reject non-admin tokens with 403.
 *
 * Phase 6.19 additions — all exposures of EXISTING verified contracts, no
 * new backend surface:
 *   - "Student Approvals" reuses the Phase 6.4 approval-queue contract
 *     (the same one the Phase 6.18 staff shell uses);
 *   - "AI Assistant" reuses the existing ChatShell (the authenticated chat
 *     contracts are `get_current_user`-authorized, so admin is allowed);
 *   - "Profile" renders the safe /auth/me identity fields.
 *
 * Session expiry is inherited, never duplicated: every request goes through
 * the shared API client (requestJson -> 401 -> notifySessionExpired ->
 * AuthProvider).
 */

import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import AdminDashboard from './AdminDashboard.tsx'
import AdminApprovals from './AdminApprovals.tsx'
import AdminProfile from './AdminProfile.tsx'
import FaqManager from './FaqManager.tsx'
import DocumentManager from './DocumentManager.tsx'
import NoticeManager from './NoticeManager.tsx'
import StudentManager from './StudentManager.tsx'
import ResultsManager from './ResultsManager.tsx'
import TestResultsManager from './TestResultsManager.tsx'
import AttendanceManager from './AttendanceManager.tsx'
import { ADMIN_VIEW_HEADINGS, buildAdminNavigation, type AdminView } from './adminNavigation.ts'

export default function AdminShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [currentView, setCurrentView] = useState<AdminView>('dashboard')
  const navigation = buildAdminNavigation(role)

  // Phase 6.15.4 — identity comes from the canonical /auth/me bootstrap
  // (AuthProvider state). App.tsx only renders this shell once /auth/me has
  // resolved the authenticated identity, so `user` is present.
  const identityLabel = user?.email?.trim() || 'Admin'

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 bg-slate-800/60">
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <div className="mr-auto min-w-0">
            <p className="text-lg font-bold text-white">Admin Panel</p>
            <p className="break-words text-xs text-slate-400">Signed in as {identityLabel}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            Sign out
          </button>
        </div>
        {navigation.length > 0 ? (
          <nav aria-label="Admin navigation" className="mx-auto w-full max-w-7xl px-4 pb-3">
            <ul className="flex flex-wrap gap-2">
              {navigation.map((item) => {
                const active = item.key === currentView
                return (
                  <li key={item.key}>
                    <button
                      type="button"
                      onClick={() => setCurrentView(item.key)}
                      aria-current={active ? 'page' : undefined}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-400 ${
                        active
                          ? 'bg-emerald-600 text-white'
                          : 'border border-slate-600 text-slate-200 hover:bg-slate-700'
                      }`}
                    >
                      {item.label}
                    </button>
                  </li>
                )
              })}
            </ul>
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full min-w-0 max-w-7xl px-4 py-6">
        {user === null ? (
          <section
            role="status"
            className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center"
          >
            <h1 className="text-2xl font-bold text-white">Admin workspace unavailable</h1>
            <p className="mt-3 text-sm text-slate-300">
              Your administrator identity could not be loaded. Please sign in again.
            </p>
            <button
              type="button"
              onClick={logout}
              className="mt-6 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              Sign out
            </button>
          </section>
        ) : (
          <>
            {currentView !== 'assistant' ? (
              <h1 className="mb-4 break-words text-2xl font-bold text-white">
                {ADMIN_VIEW_HEADINGS[currentView]}
              </h1>
            ) : null}
            {currentView === 'dashboard' ? <AdminDashboard /> : null}
            {currentView === 'approvals' ? (
              accessToken !== null ? (
                <AdminApprovals accessToken={accessToken} />
              ) : (
                <section
                  role="status"
                  className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center"
                >
                  <p className="text-sm text-slate-300">
                    Your session could not be verified. Please sign in again.
                  </p>
                </section>
              )
            ) : null}
            {currentView === 'students' ? <StudentManager /> : null}
            {currentView === 'attendance' ? <AttendanceManager /> : null}
            {currentView === 'results' ? <ResultsManager /> : null}
            {currentView === 'test-results' ? <TestResultsManager /> : null}
            {currentView === 'notices' ? <NoticeManager /> : null}
            {currentView === 'documents' ? <DocumentManager /> : null}
            {currentView === 'faqs' ? <FaqManager /> : null}
            {currentView === 'assistant' ? (
              <section aria-label="AI Assistant">
                <ChatShell />
              </section>
            ) : null}
            {currentView === 'profile' ? <AdminProfile user={user} /> : null}
          </>
        )}
      </main>
    </div>
  )
}

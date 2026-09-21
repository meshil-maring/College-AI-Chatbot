/**
 * Phase 6.17 — Authenticated faculty application shell.
 *
 * The shell REUSES the existing ChatShell for the assistant surface and the
 * existing AuthProvider identity — it does NOT duplicate chat, session,
 * token, or role handling, and it does NOT add a second role-detection
 * request: selection happens in `App.tsx` from the server-authoritative
 * /auth/me role.
 *
 * Navigation (Dashboard / AI Assistant / Profile) is derived from
 * `facultyNavigation.ts`, which contains ONLY server-verified faculty
 * capabilities. Every faculty member sees the same shell regardless of how
 * they reached it; the backend remains the authorization boundary (faculty
 * requests against student/admin surfaces fail closed server-side).
 *
 * Loading/empty/error discipline: the shell is only rendered once
 * /auth/me has authenticated the session, so the dashboard never shows a
 * fabricated mid-load state. A missing identity (defensive) renders a
 * controlled neutral state with sign-out instead of partial data.
 */

import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import {
  FACULTY_VIEW_HEADINGS,
  buildFacultyNavigation,
  type FacultyView,
} from './facultyNavigation.ts'
import FacultyDashboard from './FacultyDashboard.tsx'
import FacultyProfile from './FacultyProfile.tsx'

export default function FacultyShell() {
  const { user, role, logout } = useAuth()
  const [view, setView] = useState<FacultyView>('dashboard')
  const navigation = buildFacultyNavigation(role)

  const displayName = user?.email?.trim() || 'Faculty'

  return (
    <div className="min-h-screen overflow-x-clip bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 bg-slate-800/60">
        <div className="mx-auto flex w-full min-w-0 max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <div className="mr-auto min-w-0">
            <p className="break-words text-lg font-bold text-white">College AI Chatbot</p>
            <p className="break-words text-xs text-slate-400">Signed in as {displayName}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            Sign out
          </button>
        </div>
        <nav aria-label="Faculty navigation" className="mx-auto w-full max-w-6xl px-4 pb-3">
          <ul className="flex flex-wrap gap-2">
            {navigation.map((item) => {
              const active = item.key === view
              return (
                <li key={item.key}>
                  <button
                    type="button"
                    onClick={() => setView(item.key)}
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
      </header>

      <main className="mx-auto w-full min-w-0 max-w-6xl px-4 py-6">
        {user === null ? (
          <section
            role="status"
            className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center"
          >
            <h1 className="text-2xl font-bold text-white">Faculty workspace unavailable</h1>
            <p className="mt-3 text-sm text-slate-300">
              Your faculty identity could not be loaded. Please sign in again.
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
            {view !== 'assistant' ? (
              <h1 className="mb-4 break-words text-2xl font-bold text-white">
                {FACULTY_VIEW_HEADINGS[view]}
              </h1>
            ) : null}
            {view === 'dashboard' ? <FacultyDashboard user={user} onNavigate={setView} /> : null}
            {view === 'profile' ? <FacultyProfile user={user} /> : null}
            {view === 'assistant' ? (
              <section aria-label="AI Assistant">
                <ChatShell />
              </section>
            ) : null}
          </>
        )}
      </main>
    </div>
  )
}

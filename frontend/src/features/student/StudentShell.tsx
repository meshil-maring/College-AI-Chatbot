/**
 * Phase 6.16 — Authenticated student application shell.
 *
 * Audit outcome (no duplication): the shell REUSES the existing ChatShell for
 * the assistant surface and the existing AuthProvider identity — it does NOT
 * duplicate chat, session, token, or role handling. It REPLACES the legacy
 * `AcademicsPanel` modal composition in `App.tsx` with a coherent navigation:
 *
 *   Dashboard / Attendance / Results / Notices / Learning Resources /
 *   AI Assistant / Profile
 *
 * UX ONLY — NEVER AUTHORIZATION: navigation is rendered from the
 * server-authoritative role (`/auth/me` → `user.role`). Every view calls a
 * tenant-scoped backend endpoint that re-resolves identity server-side.
 */

import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import {
  STUDENT_VIEW_HEADINGS,
  buildStudentNavigation,
  type StudentView,
} from './studentNavigation.ts'
import StudentDashboard from './StudentDashboard.tsx'
import { AttendancePage, NoticesPage, ProfilePage, ResourcesPage, ResultsPage } from './StudentPages.tsx'

export default function StudentShell() {
  const { user, role, logout } = useAuth()
  const [view, setView] = useState<StudentView>('dashboard')
  const navigation = buildStudentNavigation(role)

  const displayName =
    user?.email?.trim() ||
    'Student'

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
        <nav aria-label="Student navigation" className="mx-auto w-full max-w-6xl px-4 pb-3">
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
        {view !== 'assistant' ? (
          <h1 className="mb-4 break-words text-2xl font-bold text-white">{STUDENT_VIEW_HEADINGS[view]}</h1>
        ) : null}
        {view === 'dashboard' ? <StudentDashboard onNavigate={setView} /> : null}
        {view === 'attendance' ? <AttendancePage /> : null}
        {view === 'results' ? <ResultsPage /> : null}
        {view === 'notices' ? <NoticesPage /> : null}
        {view === 'resources' ? <ResourcesPage /> : null}
        {view === 'profile' ? <ProfilePage /> : null}
        {view === 'assistant' ? (
          <section aria-label="AI Assistant">
            <ChatShell />
          </section>
        ) : null}
      </main>
    </div>
  )
}

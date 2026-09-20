/**
 * Phase Admin-4 — Admin shell.
 *
 * Navigation container for the admin section. Uses simple state-based
 * navigation (no React Router). Provides a sidebar with links to each
 * manager and renders the active panel.
 *
 * Phase 6.15.4 — the parent (App.tsx) gates this shell on the SERVER-
 * authoritative `admin` role from /auth/me. This shell no longer re-probes
 * GET /admin/me for identity: the canonical identity (email/user id) comes
 * from the same AuthProvider state, so one authenticated request bootstraps
 * everything. Authorization itself remains fully backend-enforced: every
 * admin API request still carries the bearer token and /admin/* endpoints
 * reject non-admin tokens with 403.
 */

import { useCallback, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import AdminDashboard from './AdminDashboard.tsx'
import FaqManager from './FaqManager.tsx'
import DocumentManager from './DocumentManager.tsx'
import NoticeManager from './NoticeManager.tsx'
import StudentManager from './StudentManager.tsx'
import ResultsManager from './ResultsManager.tsx'
import TestResultsManager from './TestResultsManager.tsx'
import AttendanceManager from './AttendanceManager.tsx'

type AdminView =
  | 'dashboard'
  | 'faqs'
  | 'documents'
  | 'notices'
  | 'students'
  | 'results'
  | 'test-results'
  | 'attendance'

const NAV_ITEMS: { key: AdminView; label: string }[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'faqs', label: 'FAQs' },
  { key: 'documents', label: 'Documents' },
  { key: 'notices', label: 'Notices' },
  { key: 'students', label: 'Students' },
  { key: 'results', label: 'Results' },
  { key: 'test-results', label: 'Test Results' },
  { key: 'attendance', label: 'Attendance' },
]

export default function AdminShell() {
  const { user, logout } = useAuth()
  const [currentView, setCurrentView] = useState<AdminView>('dashboard')

  const handleLogout = useCallback(() => {
    logout()
  }, [logout])

  // Phase 6.15.4 — identity comes from the canonical /auth/me bootstrap
  // (AuthProvider state). No loading/probe state is needed: App.tsx only
  // renders this shell once /auth/me has resolved the authenticated
  // identity, so `user` is present. Defensive fallback to the user id.
  const identityLabel = user?.email ?? user?.user_id ?? 'Admin'

  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      <header className="border-b border-slate-700 bg-slate-800/60 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="text-lg font-bold text-white">Admin Panel</h1>
          <span className="text-xs text-slate-400">{identityLabel}</span>
          <div className="ml-auto flex items-center gap-3">
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 border-r border-slate-700 bg-slate-900 overflow-y-auto" aria-label="Admin navigation">
          <nav className="flex flex-col gap-1 p-2">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setCurrentView(item.key)}
                aria-current={currentView === item.key ? 'page' : undefined}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400 ${
                  currentView === item.key
                    ? 'bg-emerald-900/40 border border-emerald-700 text-white'
                    : 'border border-transparent text-slate-300 hover:bg-slate-800'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 overflow-y-auto p-6">
          {currentView === 'dashboard' && <AdminDashboard />}
          {currentView === 'faqs' && <FaqManager />}
          {currentView === 'documents' && <DocumentManager />}
          {currentView === 'notices' && <NoticeManager />}
          {currentView === 'students' && <StudentManager />}
          {currentView === 'results' && <ResultsManager />}
          {currentView === 'test-results' && <TestResultsManager />}
          {currentView === 'attendance' && <AttendanceManager />}
        </main>
      </div>
    </div>
  )
}

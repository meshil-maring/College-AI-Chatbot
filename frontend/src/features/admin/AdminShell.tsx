/**
 * Phase Admin-4 — Admin shell.
 *
 * Navigation container for the admin section. Uses simple state-based
 * navigation (no React Router). Provides a sidebar with links to each
 * manager and renders the active panel.
 *
 * Role gating is performed by the parent (App.tsx) — this shell assumes
 * the authenticated user is an admin. The admin identity is fetched to
 * confirm authorization and display the current admin.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { getAdminIdentity } from '../../services/adminApi.ts'
import type { AdminIdentity } from '../../types/admin.ts'
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
  const { accessToken, logout } = useAuth()
  const [identity, setIdentity] = useState<AdminIdentity | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<AdminView>('dashboard')

  useEffect(() => {
    if (accessToken === null) return
    let cancelled = false
    void getAdminIdentity(accessToken)
      .then((me) => {
        if (!cancelled) setIdentity(me)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setAuthError(err instanceof Error ? err.message : 'Authorization failed.')
        }
      })
    return () => { cancelled = true }
  }, [accessToken])

  const handleLogout = useCallback(() => {
    logout()
  }, [logout])

  if (authError !== null) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <main className="max-w-xl w-full text-center py-16">
          <div className="rounded-2xl border border-red-900/50 bg-red-500/10 p-10 shadow-xl">
            <h1 className="text-2xl font-bold text-red-300">Access denied</h1>
            <p className="mt-4 text-slate-300">{authError}</p>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-6 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              Sign out
            </button>
          </div>
        </main>
      </div>
    )
  }

  if (identity === null) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <main className="max-w-xl w-full text-center py-16">
          <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
            <h1 className="text-2xl font-bold text-white">Loading admin…</h1>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      <header className="border-b border-slate-700 bg-slate-800/60 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="text-lg font-bold text-white">Admin Panel</h1>
          <span className="text-xs text-slate-400">{identity.email ?? identity.user_id}</span>
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

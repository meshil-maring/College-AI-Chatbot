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
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import ChatShell from '../../chat/ChatShell.tsx'
import {
  STUDENT_VIEW_HEADINGS,
  buildStudentNavigation,
  type StudentView,
} from './studentNavigation.ts'
import { StudentDashboardContent } from '../dashboard/StudentDashboard.tsx'
import { AttendanceDetailPage as AttendancePage } from '../attendance/AttendanceDetail.tsx'
import { ResultsDetailPage as ResultsPage } from '../results/ResultsDetail.tsx'
import { NoticesPage } from '../notices/NoticesPage.tsx'
import { ResourcesPage } from '../resources/ResourcesPage.tsx'
import { ProfilePage } from '../profile/ProfilePage.tsx'
import { getMyAcademicProfile } from '../../../services/students/studentApi.ts'
import { StudentAccessContext, useStudentResource, type StudentAccessDenial } from '../shared/useStudentResource.ts'
import { ErrorBlock, LoadingBlock } from '../shared/SectionState.tsx'

export default function StudentShell() {
  const { user, role, logout } = useAuth()
  const [view, setView] = useState<StudentView>('dashboard')
  const [accessDenial, setAccessDenial] = useState<StudentAccessDenial | null>(null)
  // This endpoint exposes approval state even for pending students. This is a
  // UX boundary only; each data endpoint still enforces access server-side.
  const profile = useStudentResource(getMyAcademicProfile, 'Unable to check your student account. Please try again.', '', 'academic-profile')
  const navigation = buildStudentNavigation(role, user?.effective_permissions)

  const displayName =
    user?.email?.trim() ||
    'Student'

  const approval = profile.data?.approval_status
  const inactive = profile.data?.status === 'inactive' || profile.errorCode === 'STUDENT_INACTIVE' || profile.errorCode === 'ACCOUNT_INACTIVE'
    || accessDenial === 'STUDENT_INACTIVE' || accessDenial === 'ACCOUNT_INACTIVE'
  if (profile.status !== 'loaded' || inactive || approval !== 'approved' || accessDenial !== null) {
    const loading = profile.status === 'loading' || profile.status === 'idle'
    const title = inactive ? 'Account inactive'
      : approval === 'pending' ? 'Approval pending'
        : approval === 'rejected' ? 'Registration not approved'
          : 'Student access unavailable'
    const guidance = inactive
      ? 'Your account is inactive. Contact your institution administrator for help with access.'
      : approval === 'pending'
        ? 'Your student registration is awaiting approval from your institution. You can access the dashboard after approval. Contact your institution administrator if you need help.'
        : approval === 'rejected'
          ? 'Your student registration was not approved. Contact your institution administrator to discuss your registration and next steps.'
          : accessDenial === 'STUDENT_NOT_APPROVED'
            ? 'Your account is not approved for student access. Contact your institution administrator for help with your approval status.'
            : 'Your student account access could not be confirmed. Contact your institution administrator for help.'
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-900 px-4 text-slate-100">
        <section aria-label="Student account access" className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          {loading ? <LoadingBlock label="Checking your student account…" /> : (
            <>
              <h1 className="text-2xl font-bold text-white">{title}</h1>
              {profile.status === 'error' && !inactive ? (
                <div className="mt-4"><ErrorBlock message={profile.error ?? 'Unable to check your student account.'} onRetry={profile.reload} /></div>
              ) : (
                <p role="status" className="mt-4 text-sm text-slate-300">{guidance}</p>
              )}
              {profile.status === 'loaded' && accessDenial === null ? (
                <button type="button" onClick={profile.reload} className="mt-6 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400">Check status again</button>
              ) : null}
            </>
          )}
          <button type="button" onClick={logout} className="mt-6 ml-3 rounded-lg border border-slate-600 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">Sign out</button>
        </section>
      </main>
    )
  }

  return (
    <StudentAccessContext value={setAccessDenial}>
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
        {navigation.some((item) => item.key === view) ? (
          <>
            {view !== 'assistant' ? (
              <h1 className="mb-4 break-words text-2xl font-bold text-white">{STUDENT_VIEW_HEADINGS[view]}</h1>
            ) : null}
            {view === 'dashboard' ? <StudentDashboardContent profile={profile} onNavigate={setView} /> : null}
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
          </>
        ) : (
          <section role="status" className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center">
            <h1 className="text-2xl font-bold text-white">No available views</h1>
            <p className="mt-3 text-sm text-slate-300">
              Your account has no permissions for the selected student view.
            </p>
          </section>
        )}
      </main>
    </div>
    </StudentAccessContext>
  )
}

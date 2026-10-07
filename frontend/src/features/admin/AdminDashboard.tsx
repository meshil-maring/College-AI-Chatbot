/**
 * Phase 7.21 — University Admin operational dashboard.
 *
 * Reuses the existing `AdminDashboard` (Phase Admin-4 / 6.19) rather than
 * adding a second one, and keeps its proven behaviour: exactly one
 * `GET /api/v1/admin/dashboard` request per load, an explicit loading status,
 * an explicit error state with a manual Retry, and NO aggressive automatic
 * retry.
 *
 * What changed and why:
 *  - The payload is now the typed, institution-scoped `DashboardSummary`
 *    (institution / students / knowledge / communication / academics /
 *    quick_actions) instead of a flat count bag plus a raw `recent_audit` feed.
 *    Raw audit rows are internals (actor ids, record_data, ip, user agent) and
 *    are no longer fetched or rendered at all.
 *  - Quick actions navigate through the EXISTING AdminShell views. This
 *    component never creates a feature; it only switches the shell's view,
 *    which is the same mechanism the header navigation already uses.
 *  - Zero is a first-class value, not an error: a brand-new institution renders
 *    zeros with an explicit "nothing here yet" affordance.
 *  - A `null` metric (see `DashboardKnowledge.failed_processing_runs`) renders
 *    as "Unavailable" and is never coerced to 0.
 *
 * UX ONLY — NEVER AUTHORIZATION: hiding or showing a card cannot grant access.
 * Every target screen re-authorizes server-side through the same
 * `require_institution_roles("admin")` dependency.
 */

import type { ReactNode } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import { getDashboardSummary } from '../../services/adminApi.ts'
import type { AdminView } from './adminNavigation.ts'
import type { DashboardSummary } from '../../types/admin.ts'

interface AdminDashboardProps {
  /** Switch the AdminShell to an existing view (quick actions). */
  onNavigate?: (view: AdminView) => void
}

/** One metric tile. `value === null` renders as "Unavailable", never as 0. */
function MetricTile({
  label,
  value,
  tone = 'default',
}: {
  label: string
  value: number | null
  tone?: 'default' | 'accent'
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
      <div
        className={
          tone === 'accent'
            ? 'text-2xl font-bold text-amber-400'
            : 'text-2xl font-bold text-emerald-400'
        }
      >
        {value === null ? '—' : value}
      </div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
      {value === null ? (
        <div className="mt-1 text-[11px] text-slate-500">Unavailable</div>
      ) : null}
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
      <h3 className="break-words text-sm font-semibold uppercase tracking-wide text-slate-300">
        {title}
      </h3>
      <div className="mt-4">{children}</div>
    </section>
  )
}

export default function AdminDashboard({ onNavigate }: AdminDashboardProps) {
  const { accessToken } = useAuth()
  const dashboardQuery = useApiQuery<DashboardSummary>(
    ['admin', 'dashboard', accessToken],
    () => getDashboardSummary(accessToken as string),
    accessToken !== null,
  )
  const summary = dashboardQuery.data ?? null
  const isLoading = dashboardQuery.isPending
  const error = dashboardQuery.isError
    ? (dashboardQuery.error instanceof Error ? dashboardQuery.error.message : 'Failed to load dashboard.')
    : null
  const load = () => { void dashboardQuery.refetch() }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div role="status" className="text-slate-400">Loading dashboard…</div>
      </div>
    )
  }

  if (error !== null) {
    return (
      <div className="space-y-4">
        <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Retry
        </button>
      </div>
    )
  }

  if (summary === null) return null

  const { institution, students, knowledge, communication, academics, quick_actions: quickActions } =
    summary

  // Zero-data institution: no students, no knowledge, no notices, no FAQs.
  const isEmptyInstitution =
    students.total === 0 &&
    knowledge.sources_total === 0 &&
    communication.active_notices === 0 &&
    communication.active_faqs === 0

  return (
    <div className="space-y-6">
      {/* A. Institution overview */}
      <section
        aria-label="Institution overview"
        className="rounded-2xl border border-slate-700 bg-slate-800/70 p-5"
      >
        <h2 className="break-words text-xl font-bold text-white">{institution.name}</h2>
        <p className="mt-1 text-sm text-slate-400">
          {institution.code !== '' ? (
            <span className="font-mono">{institution.code}</span>
          ) : (
            <span>No institution code</span>
          )}
          <span className="mx-2 text-slate-600">|</span>
          <span className="capitalize">{institution.status}</span>
        </p>
      </section>

      {isEmptyInstitution ? (
        <p className="rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3 text-sm text-slate-400">
          This institution has no students, knowledge or notices yet. Start with a quick
          action below.
        </p>
      ) : null}

      {/* Headline metrics */}
      <section aria-label="Key metrics" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricTile label="Students" value={students.total} />
        <MetricTile
          label="Pending Approvals"
          value={students.pending_approvals}
          tone={students.pending_approvals > 0 ? 'accent' : 'default'}
        />
        <MetricTile label="Active Knowledge Sources" value={knowledge.sources_active} />
        <MetricTile label="Active Notices" value={communication.active_notices} />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* B. Students */}
        <SectionCard title="Students">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricTile label="Total" value={students.total} />
            <MetricTile label="Pending" value={students.pending_approvals} />
            <MetricTile label="Approved" value={students.approved} />
            <MetricTile label="Active" value={students.active} />
          </div>
        </SectionCard>

        {/* C. Knowledge */}
        <SectionCard title="Knowledge">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricTile label="Sources" value={knowledge.sources_total} />
            <MetricTile label="Active Sources" value={knowledge.sources_active} />
            <MetricTile label="Documents" value={knowledge.documents_total} />
            <MetricTile label="Failed Processing" value={knowledge.failed_processing_runs} />
          </div>
        </SectionCard>

        {/* E. Academics */}
        <SectionCard title="Academic Overview">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MetricTile label="Attendance Records" value={academics.attendance_records} />
            <MetricTile label="Test Results" value={academics.test_results} />
            <MetricTile label="Results" value={academics.results} />
          </div>
        </SectionCard>

        {/* D. Communication */}
        <SectionCard title="Communication">
          <div className="grid grid-cols-2 gap-4">
            <MetricTile label="Active FAQs" value={communication.active_faqs} />
            <MetricTile label="Active Notices" value={communication.active_notices} />
          </div>
          <div className="mt-5">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Recent Notices
            </h4>
            {communication.recent_notices.length === 0 ? (
              <p className="mt-2 text-sm text-slate-400">No active notices.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {communication.recent_notices.map((notice, index) => (
                  // The contract exposes no notice_id; index is a stable key for
                  // this fixed, read-only summary list.
                  <li
                    key={`${notice.title}-${index}`}
                    className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3"
                  >
                    <p className="break-words text-sm font-medium text-white">{notice.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      <span className="capitalize">{notice.category}</span>
                      <span className="mx-2 text-slate-600">|</span>
                      <span className="capitalize">{notice.priority}</span>
                      {notice.published_at !== null ? (
                        <>
                          <span className="mx-2 text-slate-600">|</span>
                          {new Date(notice.published_at).toLocaleString()}
                        </>
                      ) : null}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SectionCard>
      </div>

      {/* Quick actions — every target screen already exists in AdminShell */}
      <section aria-label="Quick actions">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
          Quick Actions
        </h3>
        {quickActions.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">No quick actions available.</p>
        ) : (
          <ul className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action) => (
              <li key={action.view} className="min-w-0">
                <button
                  type="button"
                  onClick={() => onNavigate?.(action.view as AdminView)}
                  className="h-full w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-left hover:border-emerald-600/60 hover:bg-slate-700/60 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                >
                  <span className="block break-words text-sm font-medium text-white">
                    {action.label}
                  </span>
                  <span className="mt-1 block break-words text-xs text-slate-400">
                    {action.description}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

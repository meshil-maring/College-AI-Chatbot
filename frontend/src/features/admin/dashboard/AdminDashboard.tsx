import {
  AlertCircle,
  ArrowRight,
  Bell,
  BookOpen,
  CalendarCheck,
  CheckCircle2,
  CircleHelp,
  ClipboardCheck,
  ClipboardList,
  Database,
  FileCheck2,
  FileText,
  GraduationCap,
  LoaderCircle,
  RefreshCw,
  UserCheck,
  Users,
} from 'lucide-react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { getDashboardSummary } from '../../../services/admin/adminApi.ts'
import type { DashboardSummary } from '../../../types/admin.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import type { AdminView } from '../adminNavigation.ts'
import { MetricTile, SectionCard } from './DashboardCards.tsx'
interface AdminDashboardProps {
  /** Switch the AdminShell to an existing view (quick actions). */
  onNavigate?: (view: AdminView) => void
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
    ? dashboardQuery.error instanceof Error
      ? dashboardQuery.error.message
      : 'Failed to load dashboard.'
    : null
  const load = () => {
    void dashboardQuery.refetch()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div role="status" className="inline-flex items-center gap-2 text-slate-400">
          <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
          Loading dashboard…
        </div>
      </div>
    )
  }

  if (error !== null) {
    return (
      <div className="space-y-4">
        <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          <AlertCircle aria-hidden="true" className="mr-2 inline-block h-4 w-4 align-text-bottom" />
          {error}
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          <RefreshCw aria-hidden="true" className="mr-1.5 inline-block h-3.5 w-3.5 align-text-bottom" />
          Retry
        </button>
      </div>
    )
  }

  if (summary === null) return null

  const { institution, students, knowledge, communication, academics, quick_actions: quickActions } = summary

  // Zero-data institution: no students, no knowledge, no notices, no FAQs.
  const isEmptyInstitution =
    students.total === 0 &&
    knowledge.sources_total === 0 &&
    communication.active_notices === 0 &&
    communication.active_faqs === 0

  return (
    <div className="space-y-6">
      {/* A. Institution overview */}
      <section aria-label="Institution overview" className="rounded-2xl border border-slate-700 bg-slate-800/70 p-5">
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
          This institution has no students, knowledge or notices yet. Start with a quick action below.
        </p>
      ) : null}

      {/* Headline metrics */}
      <section aria-label="Key metrics" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricTile label="Students" value={students.total} icon={Users} />
        <MetricTile
          label="Pending Approvals"
          value={students.pending_approvals}
          icon={UserCheck}
          tone={students.pending_approvals > 0 ? 'accent' : 'default'}
        />
        <MetricTile label="Active Knowledge Sources" value={knowledge.sources_active} icon={BookOpen} />
        <MetricTile label="Active Notices" value={communication.active_notices} icon={Bell} />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* B. Students */}
        <SectionCard title="Students" icon={GraduationCap}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricTile label="Total" value={students.total} icon={Users} />
            <MetricTile label="Pending" value={students.pending_approvals} icon={UserCheck} />
            <MetricTile label="Approved" value={students.approved} icon={CheckCircle2} />
            <MetricTile label="Active" value={students.active} icon={GraduationCap} />
          </div>
        </SectionCard>

        {/* C. Knowledge */}
        <SectionCard title="Knowledge" icon={BookOpen}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricTile label="Sources" value={knowledge.sources_total} icon={Database} />
            <MetricTile label="Active Sources" value={knowledge.sources_active} icon={BookOpen} />
            <MetricTile label="Documents" value={knowledge.documents_total} icon={FileText} />
            <MetricTile label="Failed Processing" value={knowledge.failed_processing_runs} icon={AlertCircle} />
          </div>
        </SectionCard>

        {/* E. Academics */}
        <SectionCard title="Academic Overview" icon={ClipboardList}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MetricTile label="Attendance Records" value={academics.attendance_records} icon={CalendarCheck} />
            <MetricTile label="Test Results" value={academics.test_results} icon={ClipboardCheck} />
            <MetricTile label="Results" value={academics.results} icon={FileCheck2} />
          </div>
        </SectionCard>

        {/* D. Communication */}
        <SectionCard title="Communication" icon={Bell}>
          <div className="grid grid-cols-2 gap-4">
            <MetricTile label="Active FAQs" value={communication.active_faqs} icon={CircleHelp} />
            <MetricTile label="Active Notices" value={communication.active_notices} icon={Bell} />
          </div>
          <div className="mt-5">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Recent Notices</h4>
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
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Quick Actions</h3>
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
                  <span className="block break-words text-sm font-medium text-white">{action.label}</span>
                  <span className="mt-1 block break-words text-xs text-slate-400">{action.description}</span>
                  <ArrowRight aria-hidden="true" className="mt-3 h-4 w-4 text-emerald-400" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

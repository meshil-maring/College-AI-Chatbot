import { useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  PlatformInstitutionError,
  listPlatformAudit,
} from '../../services/platformInstitutionsApi.ts'
import type {
  PlatformAuditAction,
  PlatformAuditEntry,
  PlatformAuditPage,
} from '../../types/platform.ts'
import { useAuth } from '../auth/AuthProvider.tsx'

const PAGE_SIZE = 25

/** Human wording for each audit action, so the ledger reads as a timeline. */
const ACTION_LABELS: Record<PlatformAuditAction, string> = {
  institution_created: 'Created institution',
  institution_updated: 'Updated institution',
  institution_suspended: 'Suspended institution',
  institution_activated: 'Activated institution',
  admin_assigned: 'Assigned admin',
  institution_admin_invited: 'Invited admin',
  institution_admin_invitation_accepted: 'Accepted invitation',
  institution_admin_invitation_expired: 'Invitation expired',
  institution_admin_invitation_cancelled: 'Cancelled invitation',
  institution_admin_revoked: 'Revoked admin',
  institution_admin_invitation_email_sent: 'Invitation email sent',
  institution_admin_invitation_email_failed: 'Invitation email failed',
  institution_admin_invitation_resent: 'Invitation resent',
  institution_admin_invitation_verified: 'Invitation email verified',
}

function labelFor(action: string): string {
  return ACTION_LABELS[action as PlatformAuditAction] ?? action
}

function formatTimestamp(value: string | null): string {
  if (value === null) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

/**
 * Phase 7.14 read-only platform audit view.
 *
 * STRICTLY READ-ONLY. This component offers no create, edit or delete control,
 * because the API exposes no audit mutation endpoint at all — the ledger is
 * append-only server-side and every audit route is a GET guarded by
 * `require_super_admin`.
 *
 * As everywhere else, rendering this view is a UX affordance, never an
 * authorization decision: the backend independently refuses anonymous callers
 * (401) and every tenant role including a University Admin (403).
 */
export default function PlatformAuditView() {
  const { accessToken } = useAuth()
  const token = accessToken ?? ''

  const [offset, setOffset] = useState(0)
  const [action, setAction] = useState<PlatformAuditAction | ''>('')
  const auditQuery = useApiQuery<PlatformAuditPage>(
    ['platform', 'audit', token, offset, action],
    () => listPlatformAudit(token, {
      limit: PAGE_SIZE,
      offset,
      ...(action === '' ? {} : { action }),
    }),
    token !== '',
  )
  const page = auditQuery.data ?? null
  const loading = auditQuery.isFetching
  const error = auditQuery.isError
    ? (auditQuery.error instanceof PlatformInstitutionError
      ? auditQuery.error.message
      : 'Could not load the platform audit log. Please try again.')
    : null
  const refresh = () => { void auditQuery.refetch() }

  const entries: readonly PlatformAuditEntry[] = page?.entries ?? []
  const total = page?.total ?? 0
  const canGoBack = offset > 0
  const canGoForward = offset + PAGE_SIZE < total
return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
          Platform
        </p>
        <h1 className="mt-2 text-3xl font-bold text-white">Platform Audit</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          A read-only record of every platform management action: who acted, what they did and
          which institution it affected. Records cannot be edited or removed from this view or
          from the API.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label
            className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400"
            htmlFor="audit-action-filter"
          >
            Filter by action
          </label>
          <select
            id="audit-action-filter"
            className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400"
            value={action}
            onChange={(event) => {
              setOffset(0)
              setAction(event.target.value as PlatformAuditAction | '')
            }}
          >
            <option value="">All actions</option>
            {(Object.keys(ACTION_LABELS) as PlatformAuditAction[]).map((value) => (
              <option key={value} value={value}>
                {ACTION_LABELS[value]} (filter)
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => { void refresh() }}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300"
        >
          Refresh
        </button>
      </div>

      {error !== null ? (
        <p
          role="alert"
          className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
        >
          {error}
        </p>
      ) : null}

      {loading ? (
        <p role="status" className="text-sm text-slate-400">Loading audit records...</p>
      ) : entries.length === 0 ? (
        <p className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-8 text-center text-sm text-slate-400">
          No audit records match this view yet.
        </p>
      ) : (
        <ul className="divide-y divide-slate-800 overflow-hidden rounded-2xl border border-slate-700 bg-slate-900">
          {entries.map((entry) => (
            <li
              key={entry.audit_id}
              className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-5 py-4"
            >
              <span className="w-44 shrink-0 text-xs text-slate-500">
                {formatTimestamp(entry.performed_at)}
              </span>
              <span className="w-56 shrink-0 truncate text-sm text-slate-300">
                {entry.actor_email ?? 'Platform operator'}
              </span>
              <span className="text-sm text-slate-100">{labelFor(entry.action)}</span>
              <span className="text-xs text-slate-500">
                {entry.institution_name ?? entry.institution_id}
              </span>
              {entry.result !== 'success' ? (
                <span className="text-xs text-amber-300">{entry.result}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={!canGoBack || loading}
          onClick={() => { setOffset(Math.max(0, offset - PAGE_SIZE)) }}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-xs text-slate-500">
          {total === 0
            ? 'No records'
            : `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} of ${total}`}
        </span>
        <button
          type="button"
          disabled={!canGoForward || loading}
          onClick={() => { setOffset(offset + PAGE_SIZE) }}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}

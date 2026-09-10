/**
 * Phase Admin-4 — Admin dashboard.
 *
 * Shows aggregated counts across admin-managed tables and recent audit
 * activity. Data comes from GET /api/v1/admin/dashboard.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { getDashboardSummary } from '../../services/adminApi.ts'
import type { DashboardSummary } from '../../types/admin.ts'

export default function AdminDashboard() {
  const { accessToken } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (accessToken === null) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await getDashboardSummary(accessToken)
      setSummary(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken])

  useEffect(() => {
    void load()
  }, [load])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-slate-400">Loading dashboard…</div>
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

  const countItems: { label: string; value: number }[] = [
    { label: 'Knowledge Sources', value: summary.counts.knowledge_sources },
    { label: 'Documents', value: summary.counts.documents },
    { label: 'FAQs', value: summary.counts.faqs },
    { label: 'Notices', value: summary.counts.notices },
    { label: 'Students', value: summary.counts.students },
    { label: 'Results', value: summary.counts.student_results },
    { label: 'Test Results', value: summary.counts.test_results },
    { label: 'Attendance Records', value: summary.counts.attendance_records },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-bold text-white">Overview</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {countItems.map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-700 bg-slate-800 p-4">
              <div className="text-2xl font-bold text-emerald-400">{item.value}</div>
              <div className="mt-1 text-xs text-slate-400">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
        {summary.recent_audit.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">No recent activity.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {summary.recent_audit.map((entry) => (
              <li key={entry.audit_id} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-white">{entry.action}</span>
                  <span className="text-xs text-slate-500">{new Date(entry.performed_at).toLocaleString()}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

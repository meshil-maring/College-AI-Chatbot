/**
 * Phase Admin-4 / Phase 6.19 — Student manager.
 *
 * List the students of the administrator's OWN institution.
 *
 * Phase 6.19 hardening: the tenant is no longer a client-typed input. It is
 * derived exclusively from the server-authoritative identity held in
 * AuthProvider state (`/auth/me` -> `user.institution_id`). The manual
 * "Enter institution UUID" input — a client-controlled tenant parameter —
 * was removed: authorization always derives from the authenticated JWT
 * server-side; `?institution_id=` remains only a server-validated filter.
 * When the account has no institution linked (platform-level), a controlled
 * neutral state is shown instead of an error or a fabricated list.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { listStudents } from '../../services/adminApi.ts'
import type { Student } from '../../types/admin.ts'

export default function StudentManager() {
  const { accessToken, user } = useAuth()
  const [students, setStudents] = useState<Student[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Tenant context resolved SERVER-SIDE (never typed by the admin).
  const institutionId = user?.institution_id ?? null

  const load = useCallback(async () => {
    if (accessToken === null || institutionId === null) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listStudents(accessToken, institutionId)
      setStudents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load students.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, institutionId])

  useEffect(() => {
    if (institutionId !== null) void load()
  }, [load, institutionId])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Students</h2>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
      {institutionId === null ? (
        <p role="status" className="text-sm text-slate-400">
          No institution is linked to your administrator account, so there are
          no students to manage yet.
        </p>
      ) : isLoading ? (
        <p role="status" className="text-sm text-slate-400">Loading students…</p>
      ) : students.length === 0 ? (
        <p className="text-sm text-slate-400">No students found for your institution.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-2">Number</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Enrolled</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {students.map((s) => (
                <tr key={s.student_id} className="bg-slate-900">
                  <td className="px-4 py-2 text-white">{s.student_number}</td>
                  <td className="px-4 py-2 text-slate-300">{s.status}</td>
                  <td className="px-4 py-2 text-slate-400">{s.enrollment_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

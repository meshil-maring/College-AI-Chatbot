/**
 * Phase Admin-4 — Student manager.
 *
 * List and manage student profiles.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { listStudents } from '../../services/adminApi.ts'
import type { Student } from '../../types/admin.ts'

export default function StudentManager() {
  const { accessToken } = useAuth()
  const [students, setStudents] = useState<Student[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [institutionId, setInstitutionId] = useState('')

  const load = useCallback(async () => {
    if (accessToken === null || institutionId.trim().length === 0) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listStudents(accessToken, institutionId.trim())
      setStudents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load students.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, institutionId])

  useEffect(() => {
    if (institutionId.trim().length > 0) void load()
  }, [load, institutionId])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Students</h2>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <label className="block">
          <span className="text-xs text-slate-400">Institution ID</span>
          <input type="text" value={institutionId} onChange={(e) => setInstitutionId(e.target.value)} placeholder="Enter institution UUID" className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
        </label>
      </div>
      {institutionId.trim().length === 0 ? (
        <p className="text-sm text-slate-400">Enter an institution ID to view students.</p>
      ) : isLoading ? (
        <p className="text-sm text-slate-400">Loading students…</p>
      ) : students.length === 0 ? (
        <p className="text-sm text-slate-400">No students found.</p>
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

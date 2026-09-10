/**
 * Phase Admin-4 — Test results manager.
 *
 * View test results for a student.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { listTestResults } from '../../services/adminApi.ts'
import type { TestResult } from '../../types/admin.ts'

export default function TestResultsManager() {
  const { accessToken } = useAuth()
  const [results, setResults] = useState<TestResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [studentId, setStudentId] = useState('')

  const load = useCallback(async () => {
    if (accessToken === null || studentId.trim().length === 0) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listTestResults(accessToken, studentId.trim())
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load test results.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, studentId])

  useEffect(() => {
    if (studentId.trim().length > 0) void load()
  }, [load, studentId])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Test Results</h2>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <label className="block">
          <span className="text-xs text-slate-400">Student ID</span>
          <input type="text" value={studentId} onChange={(e) => setStudentId(e.target.value)} placeholder="Enter student UUID" className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
        </label>
      </div>
      {studentId.trim().length === 0 ? (
        <p className="text-sm text-slate-400">Enter a student ID to view test results.</p>
      ) : isLoading ? (
        <p className="text-sm text-slate-400">Loading test results…</p>
      ) : results.length === 0 ? (
        <p className="text-sm text-slate-400">No test results found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-2">Test</th>
                <th className="px-4 py-2">Score</th>
                <th className="px-4 py-2">Percentage</th>
                <th className="px-4 py-2">Grade</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {results.map((r) => (
                <tr key={r.test_result_id} className="bg-slate-900">
                  <td className="px-4 py-2 text-white">{r.test_name}</td>
                  <td className="px-4 py-2 text-slate-300">{r.scored_marks ?? '—'}/{r.max_marks ?? '—'}</td>
                  <td className="px-4 py-2 text-slate-300">{r.percentage != null ? `${r.percentage}%` : '—'}</td>
                  <td className="px-4 py-2 text-slate-300">{r.letter_grade ?? '—'}</td>
                  <td className="px-4 py-2 text-slate-400">{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

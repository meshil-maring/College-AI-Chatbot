/**
 * Phase Admin-4 / Phase 6.19 — Results manager.
 *
 * View student results and upload results via CSV.
 *
 * Phase 6.19 hardening: the tenant is derived exclusively from the
 * server-authoritative identity held in AuthProvider state
 * (`/auth/me` -> `user.institution_id`) and is sent as the required
 * `institution_id` multipart field of POST /admin/results/csv-upload —
 * the backend re-scopes it against the authenticated JWT (scope_tenant),
 * so it is a validated filter, never an authorization input. The CSV
 * response contract is the backend `CsvUploadResult`
 * ({total_rows, inserted_count, failed_count, row_errors}). When the
 * account has no institution linked, the upload control is disabled with a
 * neutral status instead of guessing a tenant.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import { listStudentResults, uploadResultsCsv } from '../../services/adminApi.ts'
import type { StudentResult } from '../../types/admin.ts'

export default function ResultsManager() {
  const { accessToken, user } = useAuth()
  // Tenant context resolved SERVER-SIDE (never typed or guessed).
  const institutionId = user?.institution_id ?? null
  const [results, setResults] = useState<StudentResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [studentId, setStudentId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (accessToken === null || studentId.trim().length === 0) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listStudentResults(accessToken, studentId.trim())
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load results.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, studentId])

  useEffect(() => {
    if (studentId.trim().length > 0) void load()
  }, [load, studentId])

  const handleCsvUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (accessToken === null || institutionId === null) return
    const file = e.target.files?.[0]
    if (file === undefined) return
    setUploading(true)
    setUploadMessage(null)
    setError(null)
    try {
      const response = await uploadResultsCsv(accessToken, file, institutionId)
      // Phase 6.19 — the backend `CsvUploadResult` contract is authoritative:
      // {total_rows, inserted_count, failed_count, row_errors}.
      if (response.failed_count > 0) {
        setUploadMessage(
          `Uploaded ${response.inserted_count} of ${response.total_rows} rows; ${response.failed_count} row(s) failed.`,
        )
      } else {
        setUploadMessage(`Successfully uploaded ${response.inserted_count} of ${response.total_rows} rows.`)
      }
      if (studentId.trim().length > 0) void load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload CSV.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }, [accessToken, studentId, load, institutionId])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Results</h2>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3">
        <label className="block">
          <span className="text-xs text-slate-400">Student ID</span>
          <input type="text" value={studentId} onChange={(e) => setStudentId(e.target.value)} placeholder="Enter student UUID" className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
        </label>
        <div>
          <label className="block">
            <span className="text-xs text-slate-400">Upload Results CSV</span>
            <input
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              disabled={uploading || institutionId === null}
              className="mt-1 block w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-500 file:disabled:opacity-50"
            />
          </label>
          {institutionId === null ? (
            <p role="status" className="mt-1 text-xs text-slate-400">
              No institution is linked to your administrator account, so CSV
              results upload is unavailable.
            </p>
          ) : null}
          {uploadMessage !== null && <p role="status" className="mt-1 text-xs text-emerald-400">{uploadMessage}</p>}
        </div>
      </div>
      {studentId.trim().length === 0 ? (
        <p className="text-sm text-slate-400">Enter a student ID to view results.</p>
      ) : isLoading ? (
        <p className="text-sm text-slate-400">Loading results…</p>
      ) : results.length === 0 ? (
        <p className="text-sm text-slate-400">No results found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">SGPA</th>
                <th className="px-4 py-2">CGPA</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {results.map((r) => (
                <tr key={r.student_result_id} className="bg-slate-900">
                  <td className="px-4 py-2 text-white">{r.result_type}</td>
                  <td className="px-4 py-2 text-slate-300">{r.sgpa ?? '—'}</td>
                  <td className="px-4 py-2 text-slate-300">{r.cgpa ?? '—'}</td>
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

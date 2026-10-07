import { useState } from 'react'
import { updateFacultyTeachingValidity } from '../../services/adminApi.ts'
import { localDateTime } from './FacultyResponsibilityManager.tsx'

export default function TeachingValidityEditor({ accessToken, assignment, onSaved }: {
  accessToken: string
  assignment: { assignment_id: string; start_at?: string; end_at?: string | null; is_active?: boolean }
  onSaved: () => void
}) {
  const [start, setStart] = useState(() => localDateTime(assignment.start_at ?? new Date().toISOString()))
  const [end, setEnd] = useState(assignment.end_at ? localDateTime(assignment.end_at) : '')
  const [active, setActive] = useState(assignment.is_active ?? true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  async function save() {
    setBusy(true); setError(null)
    try { await updateFacultyTeachingValidity(accessToken, assignment.assignment_id, { start_at: new Date(start).toISOString(), end_at: end ? new Date(end).toISOString() : null, is_active: active }); onSaved() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not update teaching assignment.') }
    finally { setBusy(false) }
  }
  return <div className="w-full space-y-2 rounded border border-slate-600 p-3">
    <label>Teaching validity start<input type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} className="ml-2 rounded bg-slate-900 p-2" /></label>
    <label>Teaching validity end<input type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} className="ml-2 rounded bg-slate-900 p-2" /></label>
    <label className="block"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Teaching enabled</label>
    {error ? <p role="alert">{error}</p> : null}
    <button disabled={busy || !start} onClick={() => void save()} className="rounded bg-emerald-700 px-3 py-2">Save teaching validity</button>
  </div>
}

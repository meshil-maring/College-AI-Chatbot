import { useRef, useState, type FormEvent } from 'react'
import { updateFacultyTeachingValidity } from '../../services/adminApi.ts'
import { localDateTime } from './FacultyResponsibilityManager.tsx'
import { buttonClass, controlClass, FieldError, periodError, primaryClass, RequestFeedback } from './facultyAssignmentUi.tsx'

export default function TeachingValidityEditor({ accessToken, assignment, onSaved, onCancel, disabled = false }: {
  accessToken: string
  assignment: { assignment_id: string; start_at?: string; assigned_at?: string; end_at?: string | null; is_active?: boolean }
  onSaved: () => void
  onCancel?: () => void
  disabled?: boolean
}) {
  const [start, setStart] = useState(() => localDateTime(assignment.start_at ?? assignment.assigned_at ?? new Date().toISOString()))
  const [end, setEnd] = useState(assignment.end_at ? localDateTime(assignment.end_at) : '')
  const [active, setActive] = useState(assignment.is_active ?? true)
  const [error, setError] = useState<unknown>(null)
  const [fields, setFields] = useState<{ start?: string; end?: string }>({})
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  async function save(event: FormEvent) {
    event.preventDefault()
    if (inFlight.current || disabled) return
    const validation = periodError(start, end, true)
    setFields(validation)
    if (Object.keys(validation).length) return
    inFlight.current = true
    setBusy(true); setError(null)
    try { await updateFacultyTeachingValidity(accessToken, assignment.assignment_id, { start_at: new Date(start).toISOString(), end_at: end ? new Date(end).toISOString() : null, is_active: active }); onSaved() }
    catch (cause) { setError(cause) }
    finally { inFlight.current = false; setBusy(false) }
  }
  return <form noValidate onSubmit={(event) => void save(event)} aria-labelledby="teaching-validity-heading" className="space-y-4 rounded-lg border border-slate-600 bg-slate-900/50 p-4">
    <h3 id="teaching-validity-heading" className="font-semibold">Manage teaching validity</h3>
    <div className="grid gap-4 sm:grid-cols-2">
      <div><label htmlFor="teaching-validity-start" className="text-sm">Teaching validity start</label><input id="teaching-validity-start" required type="datetime-local" disabled={busy || disabled} value={start} onChange={(event) => { setStart(event.target.value); setFields({}) }} aria-invalid={!!fields.start} aria-describedby={fields.start ? 'teaching-validity-start-error' : undefined} className={controlClass} /><FieldError id="teaching-validity-start-error">{fields.start}</FieldError></div>
      <div><label htmlFor="teaching-validity-end" className="text-sm">Teaching validity end</label><input id="teaching-validity-end" type="datetime-local" disabled={busy || disabled} value={end} onChange={(event) => { setEnd(event.target.value); setFields({}) }} aria-invalid={!!fields.end} aria-describedby={fields.end ? 'teaching-validity-end-error' : undefined} className={controlClass} /><FieldError id="teaching-validity-end-error">{fields.end}</FieldError></div>
    </div>
    <p className="text-xs text-slate-300">Times use your local timezone; the end time is exclusive.</p>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={busy || disabled} checked={active} onChange={(event) => setActive(event.target.checked)} className="size-4 accent-emerald-600 focus-visible:outline-2 focus-visible:outline-emerald-400" />Teaching enabled</label>
    {error ? <RequestFeedback title="Unable to update teaching validity" error={error} /> : null}
    <div className="flex flex-wrap gap-3"><button type="submit" disabled={busy || disabled} className={primaryClass}>{busy ? 'Saving…' : 'Save teaching validity'}</button>{onCancel ? <button type="button" disabled={busy} onClick={onCancel} className={buttonClass}>Cancel teaching edit</button> : null}</div>
  </form>
}

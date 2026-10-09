import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { CalendarDays, Plus, Settings, ShieldCheck, Trash2 } from 'lucide-react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { createFacultyResponsibility, getFacultyResponsibilityManagement, revokeFacultyResponsibility, updateFacultyResponsibility } from '../../services/adminApi.ts'
import type { FacultyResponsibility, ResponsibilityManagement } from '../../types/faculty.ts'
import { validityLabel } from '../faculty/responsibilities.ts'
import { adminAcademicKeys } from './adminAcademicQueries.ts'
import { buttonClass, controlClass, dangerClass, FieldError, panelClass, PanelHeading, periodError, primaryClass, RequestFeedback, StateBadge } from './facultyAssignmentUi.tsx'

export function localDateTime(value: string): string {
  const date = new Date(value)
  return Number.isFinite(date.getTime()) ? new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16) : ''
}

export function useFacultyResponsibilityManagement(accessToken: string) {
  return useApiQuery(adminAcademicKeys.responsibilities(accessToken), () => getFacultyResponsibilityManagement(accessToken), true, { cache: 'navigation' })
}

export default function FacultyResponsibilityManager({ accessToken, facultyId }: { accessToken: string; facultyId: string }) {
  const query = useFacultyResponsibilityManagement(accessToken)
  return <FacultyResponsibilityWorkspace key={facultyId} accessToken={accessToken} facultyId={facultyId} query={query} />
}

export function FacultyResponsibilityWorkspace({ accessToken, facultyId, facultyName, query }: { accessToken: string; facultyId: string; facultyName?: string; query: UseQueryResult<ResponsibilityManagement, unknown> }) {
  const [code, setCode] = useState('')
  const [scopeId, setScopeId] = useState('')
  const [start, setStart] = useState(() => localDateTime(new Date().toISOString()))
  const [end, setEnd] = useState('')
  const [active, setActive] = useState(true)
  const [editing, setEditing] = useState<FacultyResponsibility | null>(null)
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [fields, setFields] = useState<{ scope?: string; start?: string; end?: string }>({})
  const definition = code ? query.data?.definitions.find((row) => row.code === code) : query.data?.definitions[0]
  const scopeType = definition?.allowed_scope_types[0] ?? ''
  const options = useMemo(() => scopeType === 'department'
    ? (query.data?.departments ?? []).map((row) => ({ id: row.department_id, label: row.name }))
    : scopeType === 'section' ? (query.data?.sections ?? []).map((row) => ({ id: row.section_id, label: `${row.program?.name ?? row.course.name} · ${row.semester?.name ?? 'Semester'} · Section ${row.code} · ${row.academic_year?.name ?? ''}` })) : [], [scopeType, query.data])
  const selectedScope = scopeId || options[0]?.id || ''
  const scopeAvailable = options.some((option) => option.id === selectedScope)
  const locked = busy || query.isError || !facultyId

  // Preserve entries on refresh; clear a selection only when its authoritative options changed.
  useEffect(() => {
    if (!editing && scopeId && !options.some((option) => option.id === scopeId)) setScopeId('')
  }, [options, editing, scopeId])

  function edit(row: FacultyResponsibility) {
    if (inFlight.current || query.isError) return
    setEditing(row); setCode(row.responsibility_code); setScopeId(row.scope_id)
    setStart(localDateTime(row.start_at)); setEnd(row.end_at ? localDateTime(row.end_at) : ''); setActive(row.is_active)
    setFields({}); setError(null); setNotice(null)
  }

  function cancelEdit() {
    setEditing(null); setScopeId(''); setStart(localDateTime(new Date().toISOString())); setEnd(''); setActive(true); setFields({}); setError(null)
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (inFlight.current || query.isError || !facultyId || !definition) return
    const validation = { ...periodError(start, end, true), ...(!scopeAvailable ? { scope: 'Choose an available responsibility scope.' } : {}) }
    setFields(validation)
    if (Object.keys(validation).length) return
    inFlight.current = true
    setBusy(true); setError(null); setNotice(null)
    try {
      const payload = { scope_type: scopeType, scope_id: selectedScope, start_at: new Date(start).toISOString(), end_at: end ? new Date(end).toISOString() : null, is_active: active }
      if (editing) await updateFacultyResponsibility(accessToken, editing.responsibility_id, payload)
      else await createFacultyResponsibility(accessToken, { ...payload, faculty_user_id: facultyId, responsibility_code: definition.code })
      setNotice(editing ? 'Responsibility updated.' : 'Responsibility added.')
      cancelEdit()
      await query.refetch()
    } catch (cause) { setError(cause) }
    finally { inFlight.current = false; setBusy(false) }
  }

  async function revoke(id: string) {
    if (inFlight.current || query.isError || !window.confirm('Revoke this responsibility immediately?')) return
    inFlight.current = true
    setBusy(true); setError(null); setNotice(null)
    try { await revokeFacultyResponsibility(accessToken, id); setNotice('Responsibility revoked.'); if (editing?.responsibility_id === id) cancelEdit(); await query.refetch() }
    catch (cause) { setError(cause) }
    finally { inFlight.current = false; setBusy(false) }
  }

  const rows = query.data?.responsibilities.filter((row) => row.faculty_user_id === facultyId) ?? []
  return <section aria-labelledby="responsibilities-heading" className={`${panelClass} space-y-4`}>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div className="min-w-0 space-y-4">
        <PanelHeading id="responsibilities-heading" purple icon={ShieldCheck} title="Responsibilities & Assignments" description="Manage positions for the selected faculty member. Times use your local timezone; the end time is exclusive." />
        <p className="text-sm text-slate-300">{facultyName ? <>Selected faculty: <span className="font-semibold text-slate-100">{facultyName}</span></> : facultyId ? 'Responsibilities apply to the faculty member selected above.' : 'Select a faculty member in the teaching form above to manage responsibilities.'} One appointment per department or class can be active at a time.</p>
        {query.isPending ? <p role="status" className="text-sm text-slate-300">Loading responsibilities…</p> : null}
        {query.data ? <form noValidate onSubmit={(event) => void save(event)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label htmlFor="responsibility-type" className="text-sm">Responsibility <span aria-hidden="true" className="text-red-400">*</span></label><select id="responsibility-type" required disabled={locked || editing !== null || !query.data.definitions.length} value={definition?.code ?? ''} onChange={(event) => { setCode(event.target.value); setScopeId(''); setFields({}) }} className={controlClass}>{!query.data.definitions.length ? <option value="">No responsibility types available</option> : query.data.definitions.map((row) => <option key={row.code} value={row.code}>{row.name}</option>)}</select></div>
            <div><label htmlFor="responsibility-scope" className="text-sm">Responsibility scope <span aria-hidden="true" className="text-red-400">*</span></label><select id="responsibility-scope" required disabled={locked || !options.length} value={selectedScope} onChange={(event) => { setScopeId(event.target.value); setFields({}) }} aria-invalid={!!fields.scope} aria-describedby={fields.scope ? 'responsibility-scope-error' : undefined} className={controlClass}>{!scopeAvailable ? <option value={selectedScope}>{editing ? 'Current scope unavailable' : 'No eligible scopes available'}</option> : null}{options.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select><FieldError id="responsibility-scope-error">{fields.scope}</FieldError>{!options.length ? <p className="mt-1 text-sm text-slate-300">No eligible scopes are available for this responsibility.</p> : null}</div>
            <div><label htmlFor="responsibility-start" className="text-sm">Responsibility start <span aria-hidden="true" className="text-red-400">*</span></label><input id="responsibility-start" required type="datetime-local" disabled={locked} value={start} onChange={(event) => { setStart(event.target.value); setFields({}) }} aria-invalid={!!fields.start} aria-describedby={fields.start ? 'responsibility-start-error' : undefined} className={controlClass} /><FieldError id="responsibility-start-error">{fields.start}</FieldError></div>
            <div><label htmlFor="responsibility-end" className="text-sm">Responsibility end (optional)</label><input id="responsibility-end" type="datetime-local" disabled={locked} value={end} onChange={(event) => { setEnd(event.target.value); setFields({}) }} aria-invalid={!!fields.end} aria-describedby={fields.end ? 'responsibility-end-error' : undefined} className={controlClass} /><FieldError id="responsibility-end-error">{fields.end}</FieldError></div>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1"><label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={locked} checked={active} onChange={(event) => setActive(event.target.checked)} className="size-4 rounded accent-emerald-600 focus-visible:outline-2 focus-visible:outline-emerald-400" />Appointment enabled</label><p className="text-xs text-slate-300">Allow this responsibility to be active during the selected period.</p></div>
          <div className="flex flex-wrap gap-3"><button type="submit" disabled={locked || !definition || !scopeAvailable} className={primaryClass}><Plus size={18} aria-hidden="true" />{busy ? 'Saving…' : editing ? 'Save responsibility' : 'Add responsibility'}</button>{editing ? <button type="button" disabled={busy} onClick={cancelEdit} className={buttonClass}>Cancel edit</button> : null}</div>
        </form> : null}
      </div>
      <aside aria-labelledby="current-responsibilities-heading" className="min-w-0 space-y-3 rounded-lg border border-slate-700 bg-slate-950/30 p-3 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 id="current-responsibilities-heading" className="font-semibold text-white">Current Responsibilities</h3>{query.data ? <span className="rounded-full bg-slate-700 px-2.5 py-1 text-xs text-blue-100">{rows.length} {rows.length === 1 ? 'record' : 'records'}</span> : null}</div>
        {query.isFetching && query.data ? <p aria-live="polite" className="text-sm text-slate-300">Updating responsibilities…</p> : null}
        {query.data ? <><ul className="space-y-3">{rows.map((row) => <li key={row.responsibility_id} className="space-y-3 rounded-lg border border-slate-700 bg-slate-800/70 p-3">
          <div className="flex items-start gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-violet-700"><ShieldCheck size={22} aria-hidden="true" /></span><div className="min-w-0"><p className="font-semibold text-white">{row.name}<span className="sr-only"> — {row.scope_label ?? 'Scope unavailable'}</span></p><p aria-hidden="true" className="mt-1 text-sm leading-relaxed text-slate-300">{row.scope_label ?? 'Scope unavailable'}</p><p className="mt-1 flex items-start gap-1.5 text-sm leading-relaxed text-slate-300"><CalendarDays size={15} aria-hidden="true" className="mt-1 shrink-0" />{validityLabel(row)}</p><div className="mt-2"><StateBadge state={row.state} /></div></div></div>
          {!row.revoked_at ? <div className="flex flex-wrap gap-2"><button type="button" disabled={locked} onClick={() => edit(row)} className={buttonClass}><Settings size={16} aria-hidden="true" />Manage {row.name}</button><button type="button" aria-label={`Revoke ${row.name}`} disabled={locked} onClick={() => void revoke(row.responsibility_id)} className={dangerClass}><Trash2 size={16} aria-hidden="true" />Revoke</button></div> : null}
        </li>)}</ul>{rows.length === 0 && !query.isError ? <p className="py-4 text-sm leading-relaxed text-slate-300">{facultyId ? 'No responsibilities for the selected Faculty member.' : 'Select a faculty member to view their responsibilities.'}</p> : null}{query.isError ? <p className="text-xs text-slate-300">Last loaded records; refresh failed.</p> : null}</> : !query.isPending ? <p className="text-sm text-slate-300">Responsibility records are unavailable.</p> : null}
      </aside>
    </div>
    {query.isError ? <RequestFeedback title="Unable to load responsibilities" error={query.error} onRetry={() => void query.refetch()} retryLabel="Retry loading responsibilities" busy={query.isFetching || busy} /> : null}
    {error ? <RequestFeedback title="Responsibility request failed" error={error} /> : null}
    {notice ? <p role="status" className="rounded-lg border border-emerald-700 bg-emerald-950/40 p-3 text-sm text-emerald-200">{notice}</p> : null}
  </section>
}

import { useEffect, useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { createFacultyResponsibility, getFacultyResponsibilityManagement, revokeFacultyResponsibility, updateFacultyResponsibility } from '../../services/adminApi.ts'
import type { FacultyResponsibility } from '../../types/faculty.ts'
import { validityLabel } from '../faculty/responsibilities.ts'
import { adminAcademicKeys } from './adminAcademicQueries.ts'

export function localDateTime(value: string): string {
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

export default function FacultyResponsibilityManager({ accessToken, facultyId }: { accessToken: string; facultyId: string }) {
  const query = useApiQuery(adminAcademicKeys.responsibilities(accessToken), () => getFacultyResponsibilityManagement(accessToken), true, { cache: 'navigation' })
  const [code, setCode] = useState('')
  const [scopeId, setScopeId] = useState('')
  const [start, setStart] = useState(() => localDateTime(new Date().toISOString()))
  const [end, setEnd] = useState('')
  const [active, setActive] = useState(true)
  const [editing, setEditing] = useState<FacultyResponsibility | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const definition = query.data?.definitions.find((row) => row.code === code) ?? query.data?.definitions[0]
  const scopeType = definition?.allowed_scope_types[0] ?? ''
  const options = scopeType === 'department'
    ? (query.data?.departments ?? []).map((row) => ({ id: row.department_id, label: row.name }))
    : scopeType === 'section' ? (query.data?.sections ?? []).map((row) => ({ id: row.section_id, label: `${row.program?.name ?? row.course.name} · ${row.semester?.name ?? 'Semester'} · Section ${row.code} · ${row.academic_year?.name ?? ''}` })) : []
  const selectedScope = scopeId || options[0]?.id || ''
  useEffect(() => { setEditing(null); setScopeId(''); setError(null); setNotice(null) }, [facultyId])

  function edit(row: FacultyResponsibility) {
    setEditing(row); setCode(row.responsibility_code); setScopeId(row.scope_id)
    setStart(localDateTime(row.start_at)); setEnd(row.end_at ? localDateTime(row.end_at) : ''); setActive(row.is_active)
  }

  async function save() {
    if (!facultyId || !definition || !selectedScope || !start) return
    setBusy(true); setError(null); setNotice(null)
    try {
      const payload = { scope_type: scopeType, scope_id: selectedScope, start_at: new Date(start).toISOString(), end_at: end ? new Date(end).toISOString() : null, is_active: active }
      if (editing) await updateFacultyResponsibility(accessToken, editing.responsibility_id, payload)
      else await createFacultyResponsibility(accessToken, { ...payload, faculty_user_id: facultyId, responsibility_code: definition.code })
      setNotice(editing ? 'Responsibility updated.' : 'Responsibility added.'); setEditing(null)
      await query.refetch()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save responsibility.') }
    finally { setBusy(false) }
  }

  async function revoke(id: string) {
    if (!window.confirm('Revoke this responsibility immediately?')) return
    setBusy(true); setError(null); setNotice(null)
    try { await revokeFacultyResponsibility(accessToken, id); setNotice('Responsibility revoked.'); setEditing(null); await query.refetch() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not revoke responsibility.') }
    finally { setBusy(false) }
  }

  const rows = query.data?.responsibilities.filter((row) => row.faculty_user_id === facultyId) ?? []
  return <section aria-label="Responsibilities & Assignments" className="mt-6 space-y-4 border-t border-slate-600 pt-5">
    <h3 className="text-lg font-semibold">Responsibilities &amp; Assignments</h3>
    <p className="text-sm text-slate-300">Manage positions for the selected Faculty member. Times use your local timezone; the end time is exclusive. One appointment per department or class can be active at a time.</p>
    {query.isPending ? <p>Loading responsibilities…</p> : null}
    {query.isError || error ? <p role="alert">{error ?? (query.error instanceof Error ? query.error.message : 'Could not load responsibilities.')}</p> : null}
    {notice ? <p role="status">{notice}</p> : null}
    {query.data ? <>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>Responsibility<select disabled={busy || editing !== null} value={definition?.code ?? ''} onChange={(event) => { setCode(event.target.value); setScopeId('') }} className="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2">{query.data.definitions.map((row) => <option key={row.code} value={row.code}>{row.name}</option>)}</select></label>
        <label>Responsibility scope<select disabled={busy} value={selectedScope} onChange={(event) => setScopeId(event.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2">{options.map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
        <label>Responsibility start<input required type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2" /></label>
        <label>Responsibility end<input type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-900 p-2" /></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />Appointment enabled</label>
      </div>
      <button type="button" disabled={busy || !facultyId || !selectedScope || !start} onClick={() => void save()} className="rounded bg-emerald-700 px-3 py-2 disabled:opacity-50">{editing ? 'Save responsibility' : 'Add responsibility'}</button>
      {editing ? <button type="button" onClick={() => { setEditing(null); setScopeId('') }} className="ml-3 rounded border px-3 py-2">Cancel edit</button> : null}
      <ul className="space-y-3">{rows.map((row) => <li key={row.responsibility_id} className="rounded border border-slate-600 p-3">
        <p className="font-semibold">{row.name} — {row.scope_label ?? 'Scope unavailable'}</p><p className="text-sm">{validityLabel(row)}</p><p className="text-sm capitalize">{row.state}</p>
        {!row.revoked_at ? <div className="mt-2 flex gap-3"><button type="button" disabled={busy} onClick={() => edit(row)} className="rounded border px-3 py-1">Manage {row.name}</button><button type="button" disabled={busy} onClick={() => void revoke(row.responsibility_id)} className="rounded border border-red-600 px-3 py-1">Revoke {row.name}</button></div> : null}
      </li>)}</ul>
      {rows.length === 0 ? <p className="text-sm text-slate-400">No responsibilities for the selected Faculty member.</p> : null}
    </> : null}
  </section>
}

import { useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  createScopedTeachingAssignment,
  getScopedTeachingAssignments,
  revokeScopedTeachingAssignment,
  updateScopedTeachingAssignment,
} from '../../services/adminApi.ts'

function toLocalInput(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function toUtc(value: string): string {
  return new Date(value).toISOString()
}

export default function ScopedTeachingAssignmentManager({ accessToken }: { accessToken: string }) {
  const query = useApiQuery(
    ['faculty', 'scoped-teaching-assignment-management', accessToken],
    () => getScopedTeachingAssignments(accessToken),
  )
  const [facultyId, setFacultyId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [editing, setEditing] = useState<string | null>(null)
  const [editStart, setEditStart] = useState('')
  const [editEnd, setEditEnd] = useState('')
  const [editActive, setEditActive] = useState(true)
  const [busy, setBusy] = useState(false)
  const [filterFaculty, setFilterFaculty] = useState('')
  const [filterState, setFilterState] = useState('all')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function create() {
    if (!facultyId || !sectionId || !startAt) return
    if (endAt && new Date(endAt) <= new Date(startAt)) {
      setError('Teaching end must be later than the start.')
      return
    }
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await createScopedTeachingAssignment(accessToken, {
        faculty_user_id: facultyId,
        section_id: sectionId,
        start_at: toUtc(startAt),
        end_at: endAt ? toUtc(endAt) : null,
        is_active: true,
      })
      setNotice('Teaching assignment created.')
      await query.refetch()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create teaching assignment.')
    } finally {
      setBusy(false)
    }
  }

  async function save(assignmentId: string) {
    if (!editStart) {
      setError('Teaching start is required.')
      return
    }
    if (editEnd && new Date(editEnd) <= new Date(editStart)) {
      setError('Teaching end must be later than the start.')
      return
    }
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await updateScopedTeachingAssignment(accessToken, assignmentId, {
        start_at: toUtc(editStart),
        end_at: editEnd ? toUtc(editEnd) : null,
        is_active: editActive,
      })
      setEditing(null)
      setNotice('Teaching assignment updated.')
      await query.refetch()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update teaching assignment.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(assignmentId: string) {
    if (!window.confirm('Revoke this teaching assignment? Historical assignment data will be retained.')) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await revokeScopedTeachingAssignment(accessToken, assignmentId)
      setNotice('Teaching assignment revoked.')
      await query.refetch()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not revoke teaching assignment.')
    } finally {
      setBusy(false)
    }
  }

  if (query.isPending) return <p role="status">Loading scoped teaching assignments…</p>
  if (query.isError || !query.data) {
    return <div role="alert" className="space-y-2">
      <p>{query.error instanceof Error ? query.error.message : 'Could not load scoped teaching assignments.'}</p>
      <button type="button" onClick={() => void query.refetch()} className="rounded border border-slate-500 px-3 py-1.5">Retry</button>
    </div>
  }

  const data = query.data
  const now = Date.now()
  const activeCount = data.assignments.filter((assignment) => assignment.state === 'active').length
  const upcomingCount = data.assignments.filter((assignment) => assignment.state === 'scheduled').length
  const expiringCount = data.assignments.filter((assignment) => {
    if (assignment.state !== 'active' || !assignment.end_at) return false
    const end = new Date(assignment.end_at).getTime()
    return end > now && end <= now + 30 * 24 * 60 * 60 * 1000
  }).length
  const visibleAssignments = data.assignments.filter((assignment) =>
    (!filterFaculty || assignment.faculty_user_id === filterFaculty)
    && (filterState === 'all' || assignment.state === filterState),
  )
  return <section aria-labelledby="scoped-assignment-heading" className="space-y-4 rounded-xl border border-slate-600 bg-slate-900/60 p-4">
    <div>
      <h2 id="scoped-assignment-heading" className="text-lg font-semibold">Teaching assignments in your scope</h2>
      <p className="mt-1 text-sm text-slate-300">Only academic sections authorized by your active responsibility are available. Reassignment preserves the previous record; revoke it and create a successor assignment.</p>
    </div>
    {error ? <p role="alert" className="rounded border border-red-700 p-2 text-sm text-red-200">{error}</p> : null}
    {notice ? <p role="status" className="rounded border border-emerald-700 p-2 text-sm text-emerald-200">{notice}</p> : null}
    <div className="grid gap-3 md:grid-cols-2">
      <label className="text-sm">Faculty member
        <select value={facultyId} onChange={(event) => setFacultyId(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2">
          <option value="">Select faculty</option>
          {data.faculty.map((faculty) => <option key={faculty.id} value={faculty.id}>{faculty.first_name} {faculty.last_name} · {faculty.email}</option>)}
        </select>
      </label>
      <label className="text-sm">Course / section
        <select value={sectionId} onChange={(event) => setSectionId(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2">
          <option value="">Select course section</option>
          {data.sections.map((section) => <option key={section.section_id} value={section.section_id}>{section.course.code} · {section.program?.name ?? 'Program'} · {section.semester?.name ?? 'Semester'} · {section.code}</option>)}
        </select>
      </label>
      <label className="text-sm">Valid from
        <input type="datetime-local" required value={startAt} onChange={(event) => setStartAt(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2" />
      </label>
      <label className="text-sm">Valid until (optional)
        <input type="datetime-local" value={endAt} onChange={(event) => setEndAt(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2" />
      </label>
    </div>
    <button type="button" disabled={busy || !facultyId || !sectionId || !startAt} onClick={() => void create()} className="rounded bg-emerald-700 px-3 py-2 text-sm disabled:opacity-50">Create assignment</button>
    <div className="grid gap-3 sm:grid-cols-3" aria-label="Teaching load summary">
      <p className="rounded border border-slate-700 p-3 text-sm">Active assignments: <strong>{activeCount}</strong></p>
      <p className="rounded border border-slate-700 p-3 text-sm">Upcoming assignments: <strong>{upcomingCount}</strong></p>
      <p className="rounded border border-slate-700 p-3 text-sm">Expiring within 30 days: <strong>{expiringCount}</strong></p>
    </div>
    <div className="space-y-2">
      <h3 className="font-medium">Assignment history and teaching load</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">Faculty filter
          <select value={filterFaculty} onChange={(event) => setFilterFaculty(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2">
            <option value="">All faculty</option>
            {data.faculty.map((faculty) => <option key={faculty.id} value={faculty.id}>{faculty.first_name} {faculty.last_name} · {faculty.email}</option>)}
          </select>
        </label>
        <label className="text-sm">Assignment status
          <select value={filterState} onChange={(event) => setFilterState(event.target.value)} className="mt-1 block w-full rounded bg-slate-800 p-2">
            <option value="all">All states</option>
            <option value="active">Active</option>
            <option value="scheduled">Upcoming</option>
            <option value="expired">Expired</option>
            <option value="revoked">Revoked</option>
            <option value="inactive">Disabled</option>
          </select>
        </label>
      </div>
      {visibleAssignments.length === 0 ? <p className="text-sm text-slate-400">No assignments match this scope and filter.</p> : visibleAssignments.map((assignment) => (
        <article key={assignment.assignment_id} className="rounded border border-slate-700 p-3">
          <div className="flex flex-wrap items-start gap-3">
            <div className="mr-auto text-sm">
              <p className="font-medium">{assignment.faculty ? `${assignment.faculty.first_name} ${assignment.faculty.last_name}` : 'Faculty record unavailable'} · {assignment.section.course.code} · {assignment.section.code}</p>
              <p className="text-slate-300">{assignment.section.course.name} · {assignment.section.program?.name ?? 'Program'} · {assignment.section.semester?.name ?? 'Semester'}</p>
              <p className="text-xs text-slate-400">{assignment.state} · {new Date(assignment.start_at).toLocaleString()} → {assignment.end_at ? new Date(assignment.end_at).toLocaleString() : 'No end date'}</p>
            </div>
            {assignment.revoked_at ? <span className="text-xs text-slate-400">Revoked</span> : <>
              <button type="button" disabled={busy} onClick={() => {
                setEditing(editing === assignment.assignment_id ? null : assignment.assignment_id)
                setEditStart(toLocalInput(assignment.start_at))
                setEditEnd(toLocalInput(assignment.end_at))
                setEditActive(assignment.is_active)
                setError(null)
              }} className="rounded border border-slate-500 px-2 py-1 text-xs">Edit validity</button>
              <button type="button" disabled={busy} onClick={() => void revoke(assignment.assignment_id)} className="rounded border border-red-700 px-2 py-1 text-xs text-red-200">Revoke</button>
            </>}
          </div>
          {editing === assignment.assignment_id ? <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-xs">Valid from<input type="datetime-local" value={editStart} onChange={(event) => setEditStart(event.target.value)} className="mt-1 block rounded bg-slate-800 p-2" /></label>
            <label className="text-xs">Valid until<input type="datetime-local" value={editEnd} onChange={(event) => setEditEnd(event.target.value)} className="mt-1 block rounded bg-slate-800 p-2" /></label>
            <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={editActive} onChange={(event) => setEditActive(event.target.checked)} />Enabled</label>
            <button type="button" disabled={busy} onClick={() => void save(assignment.assignment_id)} className="rounded bg-sky-700 px-3 py-2 text-xs disabled:opacity-50">Save validity</button>
          </div> : null}
        </article>
      ))}
    </div>
  </section>
}

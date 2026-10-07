import { useEffect, useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  createFacultyAssignment,
  getFacultyAssignments,
  revokeFacultyAssignment,
} from '../../services/adminApi.ts'
import FacultyResponsibilityManager from './FacultyResponsibilityManager.tsx'
import TeachingValidityEditor from './TeachingValidityEditor.tsx'

type AssignmentData = Awaited<ReturnType<typeof getFacultyAssignments>>

export default function FacultyAssignmentManager({ accessToken }: { accessToken: string }) {
  const [data, setData] = useState<AssignmentData | null>(null)
  const [facultyId, setFacultyId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [teachingStart, setTeachingStart] = useState('')
  const [teachingEnd, setTeachingEnd] = useState('')
  const [editingTeaching, setEditingTeaching] = useState<string | null>(null)

  const assignmentsQuery = useApiQuery<AssignmentData>(
    ['admin', 'faculty-assignments', accessToken],
    () => getFacultyAssignments(accessToken),
  )

  function load() { void assignmentsQuery.refetch() }

  useEffect(() => {
    setLoading(assignmentsQuery.isFetching)
    if (assignmentsQuery.data) {
      setData(assignmentsQuery.data)
      setFacultyId((previous) => previous || assignmentsQuery.data.faculty[0]?.id || '')
      setSectionId((previous) => previous || assignmentsQuery.data.sections[0]?.section_id || '')
    }
    if (assignmentsQuery.isError) setError(assignmentsQuery.error instanceof Error ? assignmentsQuery.error.message : 'Could not load Faculty assignments.')
  }, [assignmentsQuery.data, assignmentsQuery.error, assignmentsQuery.isError, assignmentsQuery.isFetching])

  async function assign() {
    if (!facultyId || !sectionId) return
    if (!window.confirm('Assign this Faculty member to the selected active section?')) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await createFacultyAssignment(accessToken, { faculty_user_id: facultyId, section_id: sectionId,
        ...(teachingStart ? { start_at: new Date(teachingStart).toISOString(), end_at: teachingEnd ? new Date(teachingEnd).toISOString() : null } : {}) })
      setNotice('Faculty section assignment saved.')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create Faculty assignment.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(assignmentId: string) {
    if (!window.confirm('Revoke this Faculty section assignment?')) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await revokeFacultyAssignment(accessToken, assignmentId)
      setNotice('Faculty section assignment revoked.')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not revoke Faculty assignment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="faculty-assignment-heading" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-800 p-4">
      <h2 id="faculty-assignment-heading" className="text-lg font-semibold text-white">Faculty section assignments</h2>
      <p className="text-sm text-slate-300">Assignments are limited to active Faculty and sections in your institution.</p>
      {error ? <p role="alert" className="rounded-lg border border-red-700 p-3 text-sm text-red-200">{error}</p> : null}
      {notice ? <p role="status" className="rounded-lg border border-emerald-700 p-3 text-sm text-emerald-200">{notice}</p> : null}
      {loading ? <p role="status">Loading Faculty assignments…</p> : !data ? null : (
        <>
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <label className="text-sm">Faculty member
              <select className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2" value={facultyId} onChange={(event) => setFacultyId(event.target.value)}>
                {data.faculty.map((member) => <option key={member.id} value={member.id}>{member.first_name} {member.last_name} · {member.email}</option>)}
              </select>
            </label>
            <label className="text-sm">Section
              <select className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2" value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
                {data.sections.map((section) => <option key={section.section_id} value={section.section_id}>{section.course.code} · {section.code} — {section.name}</option>)}
              </select>
            </label>
            <button type="button" disabled={busy || !facultyId || !sectionId} onClick={() => void assign()} className="self-end rounded-lg bg-emerald-700 px-3 py-2 text-sm disabled:opacity-50">Assign section</button>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <label>Teaching start (optional)<input type="datetime-local" value={teachingStart} onChange={(event) => setTeachingStart(event.target.value)} className="ml-2 rounded bg-slate-900 p-2" /></label>
            <label>Teaching end (optional)<input type="datetime-local" disabled={!teachingStart} value={teachingEnd} onChange={(event) => setTeachingEnd(event.target.value)} className="ml-2 rounded bg-slate-900 p-2" /></label>
          </div>
          {data.assignments.length === 0 ? <p className="text-sm text-slate-400">No active Faculty assignments.</p> : (
            <ul className="divide-y divide-slate-700">
              {data.assignments.map((assignment) => (
                <li key={assignment.assignment_id} className="flex flex-wrap items-center gap-3 py-3">
                  <span className="mr-auto text-sm">
                    {assignment.faculty.first_name} {assignment.faculty.last_name} ({assignment.faculty.email})
                    <span className="block text-slate-300">
                      {assignment.section.course.code} · {assignment.section.code} — {assignment.section.name}
                    </span>
                  </span>
                  <span className="text-xs text-slate-300">{assignment.start_at ? new Date(assignment.start_at).toLocaleString() : 'Immediate'} → {assignment.end_at ? new Date(assignment.end_at).toLocaleString() : 'No end date'}{assignment.is_active === false ? ' · Disabled' : ''}</span>
                  <button type="button" disabled={busy} onClick={() => setEditingTeaching(assignment.assignment_id)} className="rounded-lg border border-slate-500 px-3 py-1.5 text-sm">Manage teaching</button>
                  <button type="button" disabled={busy} onClick={() => void revoke(assignment.assignment_id)} className="rounded-lg border border-red-700 px-3 py-1.5 text-sm text-red-200 disabled:opacity-50">Revoke</button>
                  {editingTeaching === assignment.assignment_id ? <TeachingValidityEditor accessToken={accessToken} assignment={assignment} onSaved={() => { setEditingTeaching(null); load() }} /> : null}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <FacultyResponsibilityManager accessToken={accessToken} facultyId={facultyId} />
    </section>
  )
}

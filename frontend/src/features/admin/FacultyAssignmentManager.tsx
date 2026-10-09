import { useEffect, useRef, useState, type FormEvent } from 'react'
import { BookOpen, GraduationCap, Plus, RefreshCw, RotateCcw, Search, Settings, ShieldCheck, Trash2, UserRound, Users, Info, type LucideIcon } from 'lucide-react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { createFacultyAssignment, getFacultyAssignments, revokeFacultyAssignment } from '../../services/adminApi.ts'
import { FacultyResponsibilityWorkspace, useFacultyResponsibilityManagement } from './FacultyResponsibilityManager.tsx'
import TeachingValidityEditor from './TeachingValidityEditor.tsx'
import { adminAcademicKeys, invalidateFacultyResponsibilities } from './adminAcademicQueries.ts'
import { buttonClass, controlClass, dangerClass, FieldError, panelClass, PanelHeading, periodError, primaryClass, RequestFeedback, StateBadge, teachingPeriod, teachingState } from './facultyAssignmentUi.tsx'

type AssignmentData = Awaited<ReturnType<typeof getFacultyAssignments>>

export default function FacultyAssignmentManager({ accessToken }: { accessToken: string }) {
  return <FacultyAssignmentWorkspace key={accessToken} accessToken={accessToken} />
}

function SummaryCard({ label, value, description, icon: Icon, tone, pending }: { label: string; value?: number; description: string; icon: LucideIcon; tone: string; pending: boolean }) {
  return <div role="group" aria-label={label} className={`${panelClass} flex items-center gap-4`}>
    <span className={`flex size-14 shrink-0 items-center justify-center rounded-xl text-white ${tone}`}><Icon size={28} aria-hidden="true" /></span>
    <div><h2 className="text-sm font-semibold text-blue-200">{label}</h2><p className="mt-0.5 text-2xl font-bold text-white">{value ?? (pending ? 'Loading…' : 'Unavailable')}</p><p className="mt-1 text-sm text-slate-300">{description}</p></div>
  </div>
}

function FacultyAssignmentWorkspace({ accessToken }: { accessToken: string }) {
  const [facultyId, setFacultyId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [teachingStart, setTeachingStart] = useState('')
  const [teachingEnd, setTeachingEnd] = useState('')
  const [fields, setFields] = useState<{ faculty?: string; section?: string; start?: string; end?: string }>({})
  const [editingTeaching, setEditingTeaching] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [now, setNow] = useState(Date.now)
  const facultyInput = useRef<HTMLSelectElement>(null)
  const assignmentsQuery = useApiQuery<AssignmentData>(adminAcademicKeys.assignments(accessToken), () => getFacultyAssignments(accessToken), true, { cache: 'navigation' })
  const responsibilitiesQuery = useFacultyResponsibilityManagement(accessToken)
  const data = assignmentsQuery.data
  const unavailable = assignmentsQuery.isError

  useEffect(() => {
    if (data) {
      setFacultyId((previous) => data.faculty.some((member) => member.id === previous) ? previous : data.faculty[0]?.id ?? '')
      setSectionId((previous) => data.sections.some((section) => section.section_id === previous) ? previous : data.sections[0]?.section_id ?? '')
    }
  }, [data])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  async function load() {
    await Promise.all([assignmentsQuery.refetch(), invalidateFacultyResponsibilities(accessToken)])
    setNow(Date.now())
  }

  async function assign(event: FormEvent) {
    event.preventDefault()
    if (inFlight.current || unavailable) return
    const validation = { ...periodError(teachingStart, teachingEnd), ...(!facultyId ? { faculty: 'Choose a faculty member.' } : {}), ...(!sectionId ? { section: 'Choose an eligible section.' } : {}) }
    setFields(validation)
    if (Object.keys(validation).length) return
    if (!window.confirm('Assign this Faculty member to the selected active section?')) return
    inFlight.current = true
    setBusy(true); setError(null); setNotice(null)
    try {
      await createFacultyAssignment(accessToken, { faculty_user_id: facultyId, section_id: sectionId,
        ...(teachingStart ? { start_at: new Date(teachingStart).toISOString(), end_at: teachingEnd ? new Date(teachingEnd).toISOString() : null } : {}) })
      setNotice('Faculty section assignment saved.')
      setTeachingStart(''); setTeachingEnd('')
      await load()
    } catch (cause) { setError(cause) }
    finally { inFlight.current = false; setBusy(false) }
  }

  async function revoke(assignmentId: string) {
    if (inFlight.current || unavailable || !window.confirm('Revoke this Faculty section assignment?')) return
    inFlight.current = true
    setBusy(true); setError(null); setNotice(null)
    try {
      await revokeFacultyAssignment(accessToken, assignmentId)
      setNotice('Faculty section assignment revoked.')
      if (editingTeaching === assignmentId) setEditingTeaching(null)
      await load()
    } catch (cause) { setError(cause) }
    finally { inFlight.current = false; setBusy(false) }
  }

  function clear() {
    setFacultyId(''); setSectionId(''); setTeachingStart(''); setTeachingEnd(''); setFields({}); setError(null); setNotice(null)
  }

  const states = data?.assignments.map((row) => teachingState(row, now))
  const activeCount = !unavailable && states && !states.includes('unavailable') ? states.filter((state) => state === 'active').length : undefined
  const facultyCount = activeCount !== undefined ? new Set(data?.assignments.filter((row) => teachingState(row, now) === 'active').map((row) => row.faculty_user_id)).size : undefined
  const needle = search.trim().toLocaleLowerCase()
  const rows = data?.assignments.filter((row) => `${row.faculty.first_name} ${row.faculty.last_name} ${row.faculty.email} ${row.section.course.code} ${row.section.course.name} ${row.section.code} ${row.section.name}`.toLocaleLowerCase().includes(needle)) ?? []
  const selectedFaculty = data?.faculty.find((member) => member.id === facultyId)

  function actions(row: AssignmentData['assignments'][number]) {
    return <div className="flex flex-wrap gap-2">
      <button type="button" disabled={busy || unavailable} onClick={() => setEditingTeaching(row.assignment_id)} className={buttonClass}><Settings size={16} aria-hidden="true" />Manage teaching</button>
      <button type="button" disabled={busy || unavailable} onClick={() => void revoke(row.assignment_id)} className={dangerClass}><Trash2 size={16} aria-hidden="true" />Revoke</button>
    </div>
  }

  return <section aria-labelledby="faculty-assignment-heading" className="min-w-0 space-y-4 text-slate-100">
    <header className="flex items-center gap-4 py-1">
      <span className="flex size-14 shrink-0 items-center justify-center rounded-xl bg-emerald-700 text-white"><GraduationCap size={30} aria-hidden="true" /></span>
      <div><h1 id="faculty-assignment-heading" className="text-2xl font-bold text-white sm:text-3xl">Faculty Assignments</h1><p className="mt-1 text-sm leading-relaxed text-slate-300 sm:text-base">Manage teaching assignments and responsibilities for faculty members in your institution.</p></div>
    </header>
    <div className="grid gap-3 md:grid-cols-3">
      <SummaryCard label="Active Assignments" value={activeCount} pending={assignmentsQuery.isPending} description="Faculty section assignments" icon={Users} tone="bg-blue-700" />
      <SummaryCard label="Faculty Members" value={facultyCount} pending={assignmentsQuery.isPending} description="With active assignments" icon={UserRound} tone="bg-violet-700" />
      <SummaryCard label="Active Responsibilities" value={!responsibilitiesQuery.isError ? responsibilitiesQuery.data?.responsibilities.filter((row) => row.effective_active && row.state === 'active').length : undefined} pending={responsibilitiesQuery.isPending} description="Institution faculty responsibilities" icon={ShieldCheck} tone="bg-emerald-700" />
    </div>
    {assignmentsQuery.isError ? <RequestFeedback title="Unable to load teaching assignments" error={assignmentsQuery.error} onRetry={() => void load()} retryLabel="Retry loading assignments" busy={assignmentsQuery.isFetching || busy} /> : null}
    {error ? <RequestFeedback title="Assignment request failed" error={error} /> : null}
    {notice ? <p role="status" className="rounded-lg border border-emerald-700 bg-emerald-950/40 p-3 text-sm text-emerald-200">{notice}</p> : null}
    <section aria-labelledby="create-teaching-heading" className={panelClass}>
      <PanelHeading id="create-teaching-heading" icon={BookOpen} title="Create Teaching Assignment" description="Assign a faculty member to a section for a teaching period." />
      {assignmentsQuery.isPending ? <p role="status" className="mt-4 text-sm text-slate-300">Loading Faculty assignments…</p> : data ? <div className="mt-4 grid gap-5 xl:grid-cols-[minmax(0,3fr)_minmax(240px,1fr)]">
        <form noValidate onSubmit={(event) => void assign(event)} className="min-w-0 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label htmlFor="assignment-faculty" className="text-sm">Faculty member <span aria-hidden="true" className="text-red-400">*</span></label>
              <select ref={facultyInput} id="assignment-faculty" required disabled={busy || unavailable || !data.faculty.length} aria-invalid={!!fields.faculty} aria-describedby={fields.faculty ? 'assignment-faculty-error' : undefined} className={controlClass} value={facultyId} onChange={(event) => { setFacultyId(event.target.value); setFields({}) }}>
                <option value="">Choose a faculty member</option>{data.faculty.map((member) => <option key={member.id} value={member.id}>{member.first_name} {member.last_name} · {member.email}</option>)}
              </select><FieldError id="assignment-faculty-error">{fields.faculty}</FieldError>{!data.faculty.length ? <p className="mt-2 text-sm text-slate-300">No eligible faculty members are available in your institution.</p> : null}
            </div>
            <div><label htmlFor="assignment-section" className="text-sm">Section <span aria-hidden="true" className="text-red-400">*</span></label>
              <select id="assignment-section" required disabled={busy || unavailable || !data.sections.length} aria-invalid={!!fields.section} aria-describedby={fields.section ? 'assignment-section-error' : undefined} className={controlClass} value={sectionId} onChange={(event) => { setSectionId(event.target.value); setFields({}) }}>
                <option value="">Choose a section</option>{data.sections.map((section) => <option key={section.section_id} value={section.section_id}>{section.course.code} · {section.code} — {section.name}</option>)}
              </select><FieldError id="assignment-section-error">{fields.section}</FieldError>{!data.sections.length ? <p className="mt-2 text-sm text-slate-300">No eligible sections are available. Ask your academic administrator to activate a section.</p> : null}
            </div>
            <div><label htmlFor="assignment-start" className="text-sm">Teaching start (optional)</label><input id="assignment-start" type="datetime-local" disabled={busy || unavailable} value={teachingStart} onChange={(event) => { setTeachingStart(event.target.value); setFields({}) }} aria-invalid={!!fields.start} aria-describedby={fields.start ? "teaching-timezone assignment-start-error" : "teaching-timezone"} className={controlClass} /><FieldError id="assignment-start-error">{fields.start}</FieldError></div>
            <div><label htmlFor="assignment-end" className="text-sm">Teaching end (optional)</label><input id="assignment-end" type="datetime-local" disabled={busy || unavailable} value={teachingEnd} onChange={(event) => { setTeachingEnd(event.target.value); setFields({}) }} aria-invalid={!!fields.end} aria-describedby={fields.end ? "teaching-timezone assignment-end-error" : "teaching-timezone"} className={controlClass} /><FieldError id="assignment-end-error">{fields.end}</FieldError></div>
          </div>
          <p id="teaching-timezone" className="text-xs leading-relaxed text-slate-300">Times use your local timezone; the end time is exclusive. Set a start when specifying an end.</p>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,3fr)_minmax(0,1fr)]"><button type="submit" disabled={busy || unavailable || !data.faculty.length || !data.sections.length} className={primaryClass}><Plus size={18} aria-hidden="true" />{busy ? 'Saving…' : 'Assign section'}</button><button type="button" disabled={busy} onClick={clear} className={buttonClass}><RotateCcw size={16} aria-hidden="true" />Clear form</button></div>
        </form>
        <aside className="self-center rounded-lg border border-cyan-700 bg-cyan-950/50 p-4 text-sm leading-relaxed text-slate-100"><h3 className="flex items-center gap-2 font-semibold text-cyan-300"><Info size={19} aria-hidden="true" />About teaching assignments</h3><ul className="mt-3 list-disc space-y-1 pl-5"><li>Assignments apply to eligible sections in your institution.</li><li>Teaching dates are optional.</li><li>Faculty may have multiple assignments.</li><li>Manage or revoke existing assignments below.</li></ul></aside>
      </div> : null}
    </section>
    <section aria-labelledby="current-teaching-heading" className={`${panelClass} space-y-4`}>
      <div className="flex flex-wrap items-center justify-between gap-4"><PanelHeading id="current-teaching-heading" icon={BookOpen} title="Current Teaching Assignments" description="Active and past teaching assignments for faculty members." />
        <div className="flex w-full flex-wrap gap-2 lg:w-auto"><label className="relative min-w-0 flex-1"><span className="sr-only">Search teaching assignments</span><Search size={18} aria-hidden="true" className="pointer-events-none absolute left-3 top-3 text-slate-400" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by faculty, section…" className={`${controlClass} mt-0 pl-10 lg:w-64`} /></label><button type="button" aria-label="Refresh assignments" disabled={assignmentsQuery.isFetching || busy} onClick={() => void load()} className={buttonClass}><RefreshCw size={16} aria-hidden="true" />Refresh</button></div>
      </div>
      {assignmentsQuery.isFetching && data ? <p aria-live="polite" className="text-sm text-slate-300">Updating Faculty assignments…</p> : null}
      {data ? rows.length ? <>
        <div className="hidden overflow-x-auto rounded-lg border border-slate-700 xl:block"><table className="w-full text-left text-sm"><caption className="sr-only">Teaching assignments; times use your local timezone.</caption><thead className="bg-slate-700/50 text-blue-200"><tr>{['#', 'Faculty Member', 'Section', 'Teaching Period', 'Status', 'Actions'].map((title) => <th key={title} scope="col" className="px-3 py-3 font-semibold">{title}</th>)}</tr></thead><tbody className="divide-y divide-slate-700">{rows.map((row, index) => <tr key={row.assignment_id} className="align-top"><td className="px-3 py-3">{index + 1}</td><td className="px-3 py-3"><p className="font-semibold">{row.faculty.first_name} {row.faculty.last_name}</p><p className="mt-1 break-all text-slate-300">{row.faculty.email}</p></td><td className="px-3 py-3"><p className="font-semibold">{row.section.course.code} · {row.section.code}</p><p className="mt-1 text-slate-300">{row.section.name}</p></td><td className="max-w-56 px-3 py-3 leading-relaxed text-slate-200">{teachingPeriod(row)}</td><td className="px-3 py-3"><StateBadge state={teachingState(row, now)} /></td><td className="px-3 py-3">{actions(row)}</td></tr>)}</tbody></table></div>
        <ul aria-label="Teaching assignment cards" className="grid gap-3 md:grid-cols-2 xl:hidden">{rows.map((row, index) => <li key={row.assignment_id} className="min-w-0 space-y-3 rounded-lg border border-slate-700 bg-slate-900/40 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-semibold"><span className="mr-2 text-sm text-slate-400">{index + 1}.</span>{row.faculty.first_name} {row.faculty.last_name}</p><p className="mt-1 break-all text-sm text-slate-300">{row.faculty.email}</p></div><StateBadge state={teachingState(row, now)} /></div><dl className="space-y-2 text-sm"><div><dt className="text-slate-400">Section</dt><dd>{row.section.course.code} · {row.section.code} — {row.section.name}</dd></div><div><dt className="text-slate-400">Teaching period</dt><dd className="mt-1 leading-relaxed">{teachingPeriod(row)}</dd></div></dl>{actions(row)}</li>)}</ul>
      </> : <div className="rounded-lg border border-dashed border-slate-600 p-6 text-center"><p className="font-semibold">{needle ? 'No assignments match your search.' : 'No active Faculty assignments.'}</p><p className="mt-1 text-sm text-slate-300">{needle ? 'Try another faculty name, email, or section.' : 'Create a teaching assignment to get started.'}</p><button type="button" className={`${buttonClass} mt-4`} onClick={() => needle ? setSearch('') : facultyInput.current?.focus()}>{needle ? 'Clear search' : 'Create first assignment'}</button></div> : null}
      {data ? <p className="text-sm text-slate-300">Showing {rows.length} of {data.assignments.length} assignments{unavailable ? ' · Last loaded records; refresh failed.' : ''}</p> : null}
      {editingTeaching && data?.assignments.find((row) => row.assignment_id === editingTeaching) ? <TeachingValidityEditor key={editingTeaching} accessToken={accessToken} assignment={data.assignments.find((row) => row.assignment_id === editingTeaching)!} onSaved={() => { setEditingTeaching(null); setNotice('Teaching validity saved.'); void load() }} onCancel={() => setEditingTeaching(null)} disabled={unavailable || busy} /> : null}
    </section>
    <FacultyResponsibilityWorkspace key={facultyId} query={responsibilitiesQuery} accessToken={accessToken} facultyId={facultyId} facultyName={selectedFaculty ? `${selectedFaculty.first_name} ${selectedFaculty.last_name}`.trim() : undefined} />
  </section>
}

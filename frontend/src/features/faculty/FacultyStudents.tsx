import { useState } from 'react'
import { ArrowLeft, RefreshCw, Search, UserPlus, Users } from 'lucide-react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import FacultyStudentRegistration from './FacultyStudentRegistration.tsx'
import FacultyStudentsNavigation from './FacultyStudentsNavigation.tsx'
import FacultyStudentRecordHistory from './FacultyStudentRecordHistory.tsx'
import { navigateTo, useBrowserLocation } from '../../lib/navigation.ts'
import { facultyStudentsPath, resolveFacultyRoute } from './facultyRoutes.ts'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceProfile,
  getFacultyAttendanceStudents,
  type FacultyAttendanceAssignment,
  type FacultyAttendanceRosterRow,
} from '../../services/facultyAttendanceApi.ts'

const panel = 'rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5'
const input = 'mt-1 w-full rounded-lg border border-[#304862] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c]'
const button = 'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const primaryButton = 'rounded-lg bg-[#ffc72c] px-3 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const PAGE_SIZE = 25
const STATUS_LABELS: Record<FacultyAttendanceRosterRow['roster_status'], string> = {
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  PENDING_APPROVAL: 'Pending approval',
  UNREGISTERED: 'Unregistered',
}

function attendance(value: number | null | undefined) {
  return value == null ? 'No records' : `${value.toFixed(2)}%`
}

function LoadError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return <div role="alert" className={`${panel} space-y-3 border-red-900/60`}>
    <p className="text-sm text-red-300">{error instanceof Error ? error.message : 'Student information could not be loaded.'}</p>
    <button type="button" className={button} onClick={onRetry}>Try again</button>
  </div>
}

export default function FacultyStudents(props: { accessToken: string; scopeVersion?: string }) {
  return <FacultyStudentsWorkspace key={JSON.stringify([props.accessToken, props.scopeVersion])} {...props} />
}

function FacultyStudentsWorkspace({ accessToken, scopeVersion = '' }: { accessToken: string; scopeVersion?: string }) {
  const { pathname, search } = useBrowserLocation()
  const sectionId = new URLSearchParams(search).get('section_id') ?? ''
  const page = resolveFacultyRoute(pathname)?.studentPage ?? 'roster'
  const registrationOpen = page === 'register'
  const assignmentsQuery = useApiQuery(
    ['faculty', 'students', accessToken, scopeVersion, 'sections'],
    () => getFacultyAttendanceAssignments(accessToken),
  )
  const assignments = assignmentsQuery.isError ? [] : assignmentsQuery.data ?? []
  const selected = sectionId ? assignments.find((item) => item.section_id === sectionId)
    : registrationOpen ? assignments.find((item) => item.can_manage) : assignments[0]

  return <div className="space-y-5">
    {!registrationOpen ? <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="text-2xl font-bold text-white">Students</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">Browse student rosters in your authorized sections. Registration status and attendance reflect your institution's records.</p>
      </div>
      <button type="button" className={`${button} flex items-center gap-2`} disabled={assignmentsQuery.isFetching} onClick={() => { void assignmentsQuery.refetch() }}><RefreshCw aria-hidden="true" size={16} />Refresh sections</button>
    </div> : null}
    <FacultyStudentsNavigation page={page} sectionId={selected?.section_id ?? (sectionId || undefined)} canRegister={!!selected?.can_manage} />
    {assignmentsQuery.isError ? <LoadError error={assignmentsQuery.error} onRetry={() => { void assignmentsQuery.refetch() }} />
      : assignmentsQuery.isPending ? <p role="status" className={`${panel} text-sm text-slate-400`}>Loading your sections…</p>
        : registrationOpen && !selected?.can_manage ? <section className={`${panel} space-y-4`}>
          <h1 className="text-2xl font-bold text-white">Registration unavailable</h1>
          <p role="alert" className="text-sm text-slate-400">You do not have permission to register students in this section. Choose a section you can manage from Students.</p>
        </section> : !selected ? <section className={`${panel} py-14 text-center`}>
          <Users aria-hidden="true" className="mx-auto mb-4 h-10 w-10 text-[#ffc72c]" />
          <h2 className="text-lg font-semibold text-white">{sectionId ? 'Section unavailable' : 'No student rosters available'}</h2>
          <p className="mt-2 text-sm text-slate-400">Student rosters appear when your institution grants you access to an active section.</p>
        </section> : <>
          {!registrationOpen ? <label className={`${panel} block text-sm text-slate-300`}>Section and subject
            <select className={input} value={selected.section_id} onChange={(event) => navigateTo(facultyStudentsPath(event.target.value, page), { replace: true })}>
              {assignments.map(({ section_id, section }) => <option key={section_id} value={section_id}>{section.course.code} · {section.course.name} · {section.name} ({section.code})</option>)}
            </select>
          </label> : null}
          {page === 'history' ? <FacultyStudentRecordHistory key={selected.section_id} token={accessToken} assignment={selected} />
            : <SectionStudents key={`${selected.section_id}:${page === 'waiting-approval' ? 'waiting' : 'roster'}`} token={accessToken} assignment={selected} assignments={assignments} onSectionChange={(nextSectionId) => navigateTo(facultyStudentsPath(nextSectionId, 'register'), { replace: true })} registrationOpen={registrationOpen} waitingApproval={page === 'waiting-approval'} onRegister={() => navigateTo(facultyStudentsPath(selected.section_id, 'register'))} onBack={() => navigateTo(facultyStudentsPath(selected.section_id), { replace: true })} />}
        </>}
  </div>
}

function SectionStudents({ token, assignment, assignments, onSectionChange, registrationOpen, waitingApproval, onRegister, onBack }: {
  token: string
  assignment: FacultyAttendanceAssignment
  assignments: FacultyAttendanceAssignment[]
  onSectionChange: (sectionId: string) => void
  registrationOpen: boolean
  waitingApproval: boolean
  onRegister: () => void
  onBack: () => void
}) {
  const [filters, setFilters] = useState({ search: '', registration: '', sort: 'register_number', page: 0 })
  const [draftSearch, setDraftSearch] = useState('')
  const [studentId, setStudentId] = useState<string | null>(null)
  const [registrationMessage, setRegistrationMessage] = useState('')
  const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(filters.page * PAGE_SIZE), search: filters.search, sort: filters.sort })
  if (waitingApproval) query.set('registration', 'PENDING_APPROVAL')
  else if (filters.registration) query.set('registration', filters.registration)
  const studentsQuery = useApiQuery(
    ['faculty', 'students', token, assignment.section_id, waitingApproval, filters],
    () => getFacultyAttendanceStudents(token, assignment.section_id, query),
  )
  const result = studentsQuery.isError ? undefined : studentsQuery.data
  const selectedStudent = result?.items.find((row) => row.roster_id === studentId)

  function updateFilters(next: Partial<typeof filters>) {
    setStudentId(null)
    setFilters((current) => ({ ...current, ...next, page: 0 }))
  }

  function registered(student: FacultyAttendanceRosterRow) {
    onBack()
    setRegistrationMessage(`${student.student_name} was added to ${assignment.section.name}. Registration status: ${STATUS_LABELS[student.roster_status]}.`)
    setDraftSearch('')
    updateFilters({ search: '', registration: '', sort: 'register_number' })
  }

  if (registrationOpen) {
    return studentsQuery.isError ? <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Register new student</h1>
      <LoadError error={studentsQuery.error} onRetry={() => { void studentsQuery.refetch() }} />
    </div> : <FacultyStudentRegistration token={token} assignment={assignment} assignments={assignments} onSectionChange={onSectionChange} onRegistered={registered} onCancel={onBack} />
  }

  return <>
    <section className={`${panel} space-y-4`} aria-label="Student directory">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="font-semibold text-white">{waitingApproval ? 'Waiting approval' : `${assignment.section.name} roster`}</h2><p className="mt-1 text-xs text-slate-400">{waitingApproval ? 'Students awaiting account approval in this section. An administrator or authorized staff member reviews approvals.' : `${assignment.section.course.name} · Attendance shown for this subject only.`}</p></div>
        <div className="flex flex-wrap gap-2">
          {assignment.can_manage ? <button type="button" className={`${primaryButton} flex items-center gap-2`} disabled={studentsQuery.isError} onClick={() => { setRegistrationMessage(''); setStudentId(null); onRegister() }}><UserPlus aria-hidden="true" size={16} />Register new student</button> : null}
          <button type="button" className={button} disabled={studentsQuery.isFetching} onClick={() => { setStudentId(null); void studentsQuery.refetch() }}>Refresh students</button>
        </div>
      </div>
      {registrationMessage ? <p role="status" className="rounded-lg border border-emerald-800 bg-emerald-900/20 p-3 text-sm text-emerald-200">{registrationMessage}</p> : null}
      <div className="grid items-end gap-3 md:grid-cols-[2fr_1fr_1fr]">
        <form onSubmit={(event) => { event.preventDefault(); updateFilters({ search: draftSearch.trim() }) }}>
          <label className="block text-xs text-slate-400" htmlFor="faculty-student-search">Search students</label>
          <div className="flex items-end gap-2"><input id="faculty-student-search" className={input} maxLength={128} value={draftSearch} placeholder="Name, register number, roll number or email" onChange={(event) => setDraftSearch(event.target.value)} />
            <button type="submit" className={`${button} flex items-center gap-2`}><Search aria-hidden="true" size={16} />Search</button></div>
        </form>
        {!waitingApproval ? <label className="text-xs text-slate-400">Registration status<select className={input} value={filters.registration} onChange={(event) => updateFilters({ registration: event.target.value })}><option value="">All statuses</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label> : null}
        <label className="text-xs text-slate-400">Sort by<select className={input} value={filters.sort} onChange={(event) => updateFilters({ sort: event.target.value })}><option value="register_number">Register number</option><option value="student_name">Student name</option><option value="attendance_percentage">Attendance</option></select></label>
      </div>
      {filters.search || filters.registration ? <button type="button" className="text-sm text-[#ffc72c] underline focus:outline-none focus:ring-2 focus:ring-[#ffc72c]" onClick={() => { setDraftSearch(''); updateFilters({ search: '', registration: '' }) }}>Clear filters</button> : null}
      {studentsQuery.isError ? <LoadError error={studentsQuery.error} onRetry={() => { void studentsQuery.refetch() }} />
        : studentsQuery.isPending ? <p role="status" className="py-10 text-center text-sm text-slate-400">Loading students…</p>
          : result?.items.length ? <>
            <div className="overflow-x-auto"><table className="w-full min-w-[780px] text-left text-sm">
              <caption className="sr-only">Students in {assignment.section.name}</caption>
              <thead className="border-b border-[#304862] text-xs text-slate-400"><tr>{['Student', 'Register number', 'University roll number', 'Registration', 'Attendance', 'Details'].map((label) => <th scope="col" className="px-3 py-3" key={label}>{label}</th>)}</tr></thead>
              <tbody className="divide-y divide-[#26394e]">{result.items.map((row) => <tr key={row.roster_id} className="hover:bg-[#142638]">
                <td className="px-3 py-4"><p className="font-medium text-white">{row.student_name}</p><p className="mt-1 text-xs text-slate-400">{row.email ?? 'Email not recorded'}</p></td>
                <td className="px-3 py-4">{row.register_number}</td><td className="px-3 py-4 text-slate-300">{row.university_roll_number ?? '—'}</td>
                <td className="px-3 py-4"><span className={`rounded-full px-2 py-1 text-xs ${row.roster_status === 'ACTIVE' ? 'bg-emerald-900/30 text-emerald-300' : 'bg-slate-700/50 text-slate-300'}`}>{STATUS_LABELS[row.roster_status]}</span></td>
                <td className="px-3 py-4">{attendance(row.attendance_percentage)}</td>
                <td className="px-3 py-4"><button type="button" className={button} aria-label={`View ${row.student_name}`} aria-expanded={selectedStudent?.roster_id === row.roster_id} onClick={() => setStudentId(row.roster_id)}>View student</button></td>
              </tr>)}</tbody>
            </table></div>
          </> : <div role="status" className="py-10 text-center"><h3 className="font-medium text-white">{filters.search || filters.registration ? 'No students match your filters' : waitingApproval ? 'No students waiting for approval' : 'No students in this section yet'}</h3><p className="mt-2 text-sm text-slate-400">{filters.search || filters.registration ? 'Try another search or clear the filters.' : waitingApproval ? 'There are no pending student accounts in this section.' : 'Students appear here after they are added to the section roster.'}</p></div>}
      {result ? <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#26394e] pt-4">
        <p role="status" className="text-xs text-slate-400">{result.total === 0 ? '0 students' : !result.items.length ? `0 of ${result.total} students on this page` : `${filters.page * PAGE_SIZE + 1}–${filters.page * PAGE_SIZE + result.items.length} of ${result.total} students`}</p>
        <div className="flex gap-2"><button type="button" className={button} disabled={filters.page === 0 || studentsQuery.isFetching} onClick={() => { setStudentId(null); setFilters((current) => ({ ...current, page: current.page - 1 })) }}>Previous page</button><button type="button" className={button} disabled={(filters.page + 1) * PAGE_SIZE >= result.total || studentsQuery.isFetching} onClick={() => { setStudentId(null); setFilters((current) => ({ ...current, page: current.page + 1 })) }}>Next page</button></div>
      </div> : null}
    </section>
    {selectedStudent ? <StudentDetails key={selectedStudent.roster_id} token={token} rosterId={selectedStudent.roster_id} onClose={() => setStudentId(null)} /> : null}
  </>
}

function StudentDetails({ token, rosterId, onClose }: { token: string; rosterId: string; onClose: () => void }) {
  const [page, setPage] = useState(0)
  const profileQuery = useApiQuery(
    ['faculty', 'students', token, rosterId, 'profile', page],
    () => getFacultyAttendanceProfile(token, rosterId, page * 50),
  )
  const profile = profileQuery.isError ? undefined : profileQuery.data

  return <section className={`${panel} space-y-4`} aria-label="Student details">
    <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold text-white">Student details</h2><button type="button" className={`${button} flex items-center gap-2`} onClick={onClose}><ArrowLeft aria-hidden="true" size={16} />Close details</button></div>
    {profileQuery.isError ? <LoadError error={profileQuery.error} onRetry={() => { void profileQuery.refetch() }} /> : !profile ? <p role="status" className="text-sm text-slate-400">Loading student details…</p> : <>
      <h3 className="text-xl font-semibold text-white">{profile.student.student_name}</h3>
      <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">{[
        ['Register number', profile.student.register_number], ['University roll number', profile.student.university_roll_number ?? 'Not recorded'],
        ['Email', profile.student.email ?? 'Not recorded'], ['Registration status', STATUS_LABELS[profile.student.roster_status]],
        ['Section', profile.section.name], ['Subject attendance', attendance(profile.student.attendance_percentage)],
      ].map(([label, value]) => <div key={label}><dt className="text-xs text-slate-400">{label}</dt><dd className="mt-1 break-words text-slate-100">{value}</dd></div>)}</dl>
      <div className="border-t border-[#26394e] pt-4"><h3 className="font-semibold text-white">Subject attendance history</h3><p className="mt-1 text-xs text-slate-400">{profile.section.course.name} · {profile.total} recorded entries</p>
        {profile.history.length ? <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs text-slate-400"><tr><th scope="col" className="py-2">Date</th><th scope="col">Attendance status</th></tr></thead><tbody className="divide-y divide-[#26394e]">{profile.history.map((record) => <tr key={record.record_id}><td className="py-3">{record.session_date}</td><td className="capitalize">{record.status}</td></tr>)}</tbody></table></div> : <p className="mt-4 text-sm text-slate-400">No attendance history for this subject.</p>}
        <div className="mt-4 flex items-center justify-end gap-3"><button type="button" className={button} disabled={page === 0 || profileQuery.isFetching} onClick={() => setPage(page - 1)}>Previous records</button><span className="text-xs text-slate-400">Page {page + 1}</span><button type="button" className={button} disabled={(page + 1) * 50 >= profile.total || profileQuery.isFetching} onClick={() => setPage(page + 1)}>Next records</button></div>
      </div>
    </>}
  </section>
}

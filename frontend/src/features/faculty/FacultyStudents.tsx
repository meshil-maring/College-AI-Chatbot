import { useState } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Hourglass,
  RefreshCw,
  UserPlus,
  Users,
} from 'lucide-react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import FacultyStudentRegistration from './FacultyStudentRegistration.tsx'
import FacultyStudentRecordHistory from './FacultyStudentRecordHistory.tsx'
import ClassRegistrationDirectory from './ClassRegistrationDirectory.tsx'
import type { ClassStudentRegistration } from '../../services/studentRegistrationApi.ts'
import { navigateTo } from '../../lib/navigation.ts'
import { facultyStudentsPath, type FacultyStudentPage } from './facultyRoutes.ts'
import { useFacultyStudentSections } from './useFacultyStudentSections.ts'
import { StudentsPageHeader, StudentsSearch, StudentsStats } from '../students/StudentsUI.tsx'
import { useStudentWorkspaceApi } from '../students/StudentWorkspaceContext.tsx'
import StudentRosterFilters from '../students/StudentRosterFilters.tsx'
import type { StudentRegistrationMethod } from '../students/studentsNavigation.ts'
import {
  type FacultyAttendanceAssignment,
  type FacultyAttendanceRosterRow,
} from '../../services/facultyAttendanceApi.ts'

const panel = 'rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5'
const button = 'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const PAGE_SIZE = 25
type RosterStatus = FacultyAttendanceRosterRow['roster_status']
const STATUS_LABELS: Record<RosterStatus, string> = {
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  PENDING_APPROVAL: 'Pending approval',
  UNREGISTERED: 'Unregistered',
}
/** Row/pill tone per roster status — matches the admin students design palette. */
const STATUS_TONE: Record<RosterStatus, string> = {
  ACTIVE: 'valid',
  PENDING_APPROVAL: 'invalid',
  UNREGISTERED: 'duplicate',
  INACTIVE: '',
}
const ROSTER_STATUS_CARDS = [
  { status: 'ACTIVE', title: 'Active Students', description: 'Approved and active', Icon: CheckCircle2 },
  { status: 'PENDING_APPROVAL', title: 'Pending Approval', description: 'Awaiting account approval', Icon: Hourglass },
  { status: 'UNREGISTERED', title: 'Unregistered Students', description: 'No linked student account', Icon: AlertCircle },
  { status: 'INACTIVE', title: 'Inactive Students', description: 'Registered but disabled', Icon: AlertTriangle },
] as const
const STUDENT_PAGE_LABELS: Record<FacultyStudentPage, string> = {
  roster: 'Roster',
  history: 'Record history',
  'waiting-approval': 'Waiting approval',
  register: 'Register',
}

function attendance(value: number | null | undefined) {
  return value == null ? 'No records' : `${value.toFixed(2)}%`
}

function LoadError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return <div role="alert" className="students-alert error">
    <AlertCircle aria-hidden="true" />
    <span>{error instanceof Error ? error.message : 'Student information could not be loaded.'}</span>
    <button type="button" className="students-button" onClick={onRetry}>Try again</button>
  </div>
}

/** Server-side count of one roster status for the selected section (limit 1 — total only). */
function useRosterStatusCount(token: string, sectionId: string, status: RosterStatus, enabled: boolean, batchId: string) {
  const api = useStudentWorkspaceApi()
  return useApiQuery(
    [api.namespace, 'students', token, sectionId, 'status-count', status, batchId],
    () => api.getStudents(token, sectionId, new URLSearchParams({ registration: status, limit: '1', offset: '0', ...(batchId ? { batch_id: batchId } : {}) })),
    enabled,
  )
}

export default function FacultyStudents(props: { accessToken: string; scopeVersion?: string }) {
  return <FacultyStudentsWorkspace key={JSON.stringify([props.accessToken, props.scopeVersion])} {...props} />
}

function FacultyStudentsWorkspace({ accessToken, scopeVersion = '' }: { accessToken: string; scopeVersion?: string }) {
  const scope = useFacultyStudentSections(accessToken, scopeVersion)
  return <StudentWorkspace {...scope} accessToken={accessToken} onNavigate={(page, id, replace) => navigateTo(facultyStudentsPath(id, page), { replace })} />
}

export function StudentWorkspace({ accessToken, page, sectionId, assignmentsQuery, assignments, selected, onNavigate, registrationMethod, onRegistrationMethod, initialSearch }: {
  accessToken: string
  page: FacultyStudentPage
  sectionId: string
  assignmentsQuery: Pick<UseQueryResult<FacultyAttendanceAssignment[], unknown>, 'isError' | 'isPending' | 'isFetching' | 'error' | 'refetch'>
  assignments: FacultyAttendanceAssignment[]
  selected?: FacultyAttendanceAssignment
  onNavigate: (page: FacultyStudentPage, sectionId: string, replace?: boolean) => void
  registrationMethod?: StudentRegistrationMethod
  onRegistrationMethod?: (method: StudentRegistrationMethod) => void
  initialSearch?: string
}) {
  const api = useStudentWorkspaceApi()
  const registrationOpen = page === 'register'
  const [batchSelection, setBatchSelection] = useState({ programId: '', batchId: '' })
  const programId = selected?.section.program_id ?? selected?.section.program?.program_id ?? ''
  const batchId = batchSelection.programId === programId ? batchSelection.batchId : ''
  const changeBatch = (id: string) => setBatchSelection({ programId, batchId: id })

  return <div className="students-content students-scope">
    <StudentsPageHeader page={STUDENT_PAGE_LABELS[page]} title={registrationOpen ? undefined : 'Students'} description={api.namespace === 'admin' ? "Browse student rosters across your institution. Registration status and attendance reflect your institution's records." : "Browse student rosters in your authorized sections. Registration status and attendance reflect your institution's records."} />
    {assignmentsQuery.isError ? <LoadError error={assignmentsQuery.error} onRetry={() => { void assignmentsQuery.refetch() }} />
      : assignmentsQuery.isPending ? <p role="status" className={`${panel} text-sm text-slate-400`}>Loading your sections…</p>
        : registrationOpen && !selected?.can_manage && (api.namespace !== 'admin' || assignments.length > 0) ? <section className={`${panel} space-y-4`}>
          <h1 className="text-2xl font-bold text-white">Registration unavailable</h1>
          <p role="alert" className="text-sm text-slate-400">You do not have permission to register students in this section. Choose a section you can manage from Students.</p>
        </section> : !selected ? <section className="students-empty">
          <Users aria-hidden="true" className="mx-auto mb-4 h-10 w-10 text-[#ffc72c]" />
          <h2 className="text-lg font-semibold text-white">{sectionId ? 'Section unavailable' : 'No student rosters available'}</h2>
          <p className="mt-2 text-sm text-slate-400">{api.namespace === 'admin' ? 'Create active sections in Academic Setup before managing student rosters.' : 'Student rosters appear when your institution grants you access to an active section.'}</p>
          <button type="button" className="students-button" disabled={assignmentsQuery.isFetching} onClick={() => void assignmentsQuery.refetch()}>Refresh sections</button>
        </section> : <>
          {!registrationOpen ? <StudentRosterFilters key={`filters:${selected.section_id}`} token={accessToken} assignments={assignments} selected={selected} batchId={batchId} onBatch={changeBatch} onSection={(id) => onNavigate(page, id, true)} onRefresh={() => { void assignmentsQuery.refetch() }} refreshing={assignmentsQuery.isFetching} showBatch={page !== 'history'} /> : null}
          {page === 'history' ? <FacultyStudentRecordHistory key={selected.section_id} token={accessToken} assignment={selected} />
            : <SectionStudents key={`${selected.section_id}:${page === 'waiting-approval' ? 'waiting' : 'roster'}:${initialSearch ?? ''}`} token={accessToken} assignment={selected} assignments={assignments} batchId={batchId} onClearBatch={() => changeBatch('')} onSectionChange={(nextSectionId) => onNavigate('register', nextSectionId, true)} registrationOpen={registrationOpen} waitingApproval={page === 'waiting-approval'} onRegister={() => onNavigate('register', selected.section_id)} onBack={() => onNavigate('roster', selected.section_id, true)} registrationMethod={registrationMethod} onRegistrationMethod={onRegistrationMethod} initialSearch={initialSearch} />}
        </>}
  </div>
}

function SectionStudents({ token, assignment, assignments, batchId, onClearBatch, onSectionChange, registrationOpen, waitingApproval, onRegister, onBack, registrationMethod, onRegistrationMethod, initialSearch }: {
  token: string
  assignment: FacultyAttendanceAssignment
  assignments: FacultyAttendanceAssignment[]
  batchId: string
  onClearBatch: () => void
  onSectionChange: (sectionId: string) => void
  registrationOpen: boolean
  waitingApproval: boolean
  onRegister: () => void
  onBack: () => void
  registrationMethod?: StudentRegistrationMethod
  onRegistrationMethod?: (method: StudentRegistrationMethod) => void
  initialSearch?: string
}) {
  const api = useStudentWorkspaceApi()
  const [filters, setFilters] = useState({ search: initialSearch ?? '', registration: '', sort: 'register_number', batchId, page: 0 })
  const [draftSearch, setDraftSearch] = useState(initialSearch ?? '')
  const [studentId, setStudentId] = useState<string | null>(null)
  const [registrationMessage, setRegistrationMessage] = useState('')
  // Reset pagination before committing the new cohort, while retaining search and status.
  if (filters.batchId !== batchId) {
    setFilters({ ...filters, batchId, page: 0 })
    setStudentId(null)
  }
  // Status counts are declared before the roster query so their fetches always
  // start first — tests rely on the roster query being the latest call.
  const countsEnabled = !registrationOpen && !waitingApproval
  const activeCount = useRosterStatusCount(token, assignment.section_id, 'ACTIVE', countsEnabled, batchId)
  const pendingApprovalCount = useRosterStatusCount(token, assignment.section_id, 'PENDING_APPROVAL', countsEnabled, batchId)
  const unregisteredCount = useRosterStatusCount(token, assignment.section_id, 'UNREGISTERED', countsEnabled, batchId)
  const inactiveCount = useRosterStatusCount(token, assignment.section_id, 'INACTIVE', countsEnabled, batchId)
  const statusCounts = { ACTIVE: activeCount, PENDING_APPROVAL: pendingApprovalCount, UNREGISTERED: unregisteredCount, INACTIVE: inactiveCount }
  const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(filters.page * PAGE_SIZE), search: filters.search, sort: filters.sort })
  if (batchId) query.set('batch_id', batchId)
  if (waitingApproval) query.set('registration', 'PENDING_APPROVAL')
  else if (filters.registration) query.set('registration', filters.registration)
  const studentsQuery = useApiQuery(
    [api.namespace, 'students', token, assignment.section_id, waitingApproval, batchId, filters],
    () => api.getStudents(token, assignment.section_id, query),
    !registrationOpen,
  )
  const result = studentsQuery.isError ? undefined : studentsQuery.data
  const totalPages = Math.max(1, Math.ceil((result?.total ?? 0) / PAGE_SIZE))
  const selectedStudent = result?.items.find((row) => row.roster_id === studentId)

  function updateFilters(next: Partial<typeof filters>) {
    setStudentId(null)
    setFilters((current) => ({ ...current, ...next, page: 0 }))
  }

  function registered(student: ClassStudentRegistration) {
    onBack()
    setRegistrationMessage(`${student.student_name} was registered in Section ${student.section_code}, batch ${student.batch_start_year}–${student.batch_end_year}. Subjects can be assigned later.`)
    setDraftSearch('')
    updateFilters({ search: '', registration: '', sort: 'register_number' })
  }

  if (registrationOpen) {
    return <FacultyStudentRegistration token={token} assignment={assignment} assignments={assignments} onSectionChange={onSectionChange} onRegistered={registered} onCancel={onBack} method={registrationMethod} onMethodChange={onRegistrationMethod} />
  }

  return <>
    <ClassRegistrationDirectory key={`${assignment.section_id}:${batchId}:${filters.search}:${filters.registration}:${filters.sort}`} token={token} sectionId={assignment.section_id} waitingApproval={waitingApproval} registration={filters.registration as RosterStatus || undefined} filters={{ batchId, search: filters.search, sort: filters.sort === 'student_name' ? 'student_name' : 'register_number' }} />
    <section className="students-directory" aria-label="Student directory">
      {waitingApproval ? null : <StudentsStats items={ROSTER_STATUS_CARDS.map(({ status, title, description, Icon }) => {
          const count = statusCounts[status]
          const selected = filters.registration === status
          return { key: status, title, description, Icon, tone: STATUS_TONE[status], selected,
            value: count.isError ? '—' : count.isPending ? '…' : count.data?.total ?? 0,
            onSelect: () => updateFilters({ registration: selected ? '' : status }) }
        })} />}
      <div className="students-toolbar">
        <div className="students-toolbar-heading">
          <h2>{waitingApproval ? 'Waiting approval' : `${assignment.section.name} roster`}</h2>
          <p>{waitingApproval ? 'Students awaiting account approval in this section. An administrator or authorized staff member reviews approvals.' : `${assignment.section.course.name} · Attendance shown for this subject only.`}</p>
        </div>
        <div className="students-table-actions">
          <StudentsSearch value={draftSearch} onChange={setDraftSearch} onSubmit={() => updateFilters({ search: draftSearch.trim() })} />
          {!waitingApproval ? <label className="students-filter-label">Registration status<select value={filters.registration} onChange={(event) => updateFilters({ registration: event.target.value })}><option value="">All statuses</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label> : null}
          <label className="students-filter-label">Sort by<select value={filters.sort} onChange={(event) => updateFilters({ sort: event.target.value })}><option value="register_number">Register number</option><option value="student_name">Student name</option><option value="attendance_percentage">Attendance</option></select></label>
          {filters.search || filters.registration || batchId ? <button type="button" className="students-button" onClick={() => { setDraftSearch(''); updateFilters({ search: '', registration: '' }); onClearBatch() }}>Clear filters</button> : null}
          <button type="button" className="students-button" disabled={studentsQuery.isFetching} onClick={() => { setStudentId(null); void studentsQuery.refetch() }}><RefreshCw aria-hidden="true" />Refresh students</button>
          {assignment.can_manage ? <button type="button" className="students-button primary" disabled={studentsQuery.isError} onClick={() => { setRegistrationMessage(''); setStudentId(null); onRegister() }}><UserPlus aria-hidden="true" />Register new student</button> : null}
        </div>
      </div>
      {registrationMessage ? <p role="status" className="rounded-lg border border-emerald-800 bg-emerald-900/20 p-3 text-sm text-emerald-200">{registrationMessage}</p> : null}
      {studentsQuery.isError ? <LoadError error={studentsQuery.error} onRetry={() => { void studentsQuery.refetch() }} />
        : studentsQuery.isPending ? <p role="status" className="py-10 text-center text-sm text-slate-400">Loading students…</p>
          : result?.items.length ? <>
            <div className="students-table-scroll"><table className="students-table directory">
              <caption className="sr-only">Students in {assignment.section.name}</caption>
              <thead><tr>{['Student', 'Register number', 'University roll number', 'Registration', 'Attendance', 'Details'].map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
              <tbody>{result.items.map((row) => <tr key={row.roster_id} className={STATUS_TONE[row.roster_status]}>
                <td className="student-name"><p className="font-medium text-white">{row.student_name}</p><p className="mt-1 text-xs text-slate-400">{row.email ?? 'Email not recorded'}</p></td>
                <td>{row.register_number}</td><td>{row.university_roll_number ?? '—'}</td>
                <td><span className={`students-status ${STATUS_TONE[row.roster_status]}`}>{STATUS_LABELS[row.roster_status]}</span></td>
                <td>{attendance(row.attendance_percentage)}</td>
                <td><button type="button" className="students-button" aria-label={`View ${row.student_name}`} aria-expanded={selectedStudent?.roster_id === row.roster_id} onClick={() => setStudentId(row.roster_id)}>View student</button></td>
              </tr>)}</tbody>
            </table></div>
          </> : <div role="status" className="students-empty"><h3 className="font-medium text-white">{filters.search || filters.registration || batchId ? 'No students match your filters' : waitingApproval ? 'No students waiting for approval' : 'No students in this section yet'}</h3><p className="mt-2 text-sm text-slate-400">{filters.search || filters.registration || batchId ? 'Try another search, batch, or clear the filters. Batch matches saved admission cohorts.' : waitingApproval ? 'There are no pending student accounts in this section.' : 'Students appear here after they are added to the section roster.'}</p></div>}
      {result ? <div className="students-pagination">
        <p role="status">{result.total === 0 ? '0 students' : !result.items.length ? `0 of ${result.total} students on this page` : `${filters.page * PAGE_SIZE + 1}–${filters.page * PAGE_SIZE + result.items.length} of ${result.total} students`}</p>
        <div>
          <button type="button" className="students-page" aria-label="Previous page" disabled={filters.page === 0 || studentsQuery.isFetching} onClick={() => { setStudentId(null); setFilters((current) => ({ ...current, page: current.page - 1 })) }}><ChevronLeft aria-hidden="true" /></button>
          {Array.from({ length: 5 }, (_, index) => Math.min(Math.max(1, filters.page - 1), Math.max(1, totalPages - 4)) + index).filter((number) => number <= totalPages).map((number) => <button key={number} type="button" className={`students-page ${filters.page + 1 === number ? 'active' : ''}`} aria-label={`Page ${number}`} aria-current={filters.page + 1 === number ? 'page' : undefined} onClick={() => { setStudentId(null); setFilters((current) => ({ ...current, page: number - 1 })) }}>{number}</button>)}
          <button type="button" className="students-page" aria-label="Next page" disabled={(filters.page + 1) * PAGE_SIZE >= result.total || studentsQuery.isFetching} onClick={() => { setStudentId(null); setFilters((current) => ({ ...current, page: current.page + 1 })) }}><ChevronRight aria-hidden="true" /></button>
        </div>
      </div> : null}
    </section>
    {selectedStudent ? <StudentDetails key={selectedStudent.roster_id} token={token} rosterId={selectedStudent.roster_id} onClose={() => setStudentId(null)} /> : null}
  </>
}

function StudentDetails({ token, rosterId, onClose }: { token: string; rosterId: string; onClose: () => void }) {
  const api = useStudentWorkspaceApi()
  const [page, setPage] = useState(0)
  const profileQuery = useApiQuery(
    [api.namespace, 'students', token, rosterId, 'profile', page],
    () => api.getProfile(token, rosterId, page * 50),
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

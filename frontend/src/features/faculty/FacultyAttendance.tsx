import { useEffect, useMemo, useRef, useState } from 'react'
import { AttendanceAcademicFilters, AttendanceRecordedViews, AttendanceStudentHistory } from './attendance/AttendanceRecordedViews.tsx'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CalendarDays,
  Check,
  Clock3,
  Download,
  Ellipsis,
  GraduationCap,
  Plus,
  Search,
  Upload,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react'
import {
  AttendanceMetric,
  AttendanceMeter,
  AttendanceStatusBadge,
} from './attendance/AttendancePrimitives.tsx'
import {
  ReviewImportStage,
  UploadFileStage,
  ValidationResultsStage,
} from './attendance/UploadAttendanceStages.tsx'
import {
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  markFacultyAttendance,
  uploadFacultyAttendance,
  getFacultyAttendanceImportReview,
  getFacultyAttendanceStudents,
  getFacultyAttendanceOverview,
  correctFacultyAttendanceImportRow,
  type AttendanceOverview,
  type FacultyAttendanceAssignment,
  type FacultyAttendanceImportReview,
  type FacultyAttendanceRosterRow,
} from '../../services/facultyAttendanceApi.ts'

type AttendanceValue = 'present' | 'absent' | 'late' | 'excused'
type UploadStep = 1 | 2 | 3 | 4
type AttendanceTab = 'students' | 'history' | 'sessions' | 'reports'
type ImportedStats = { percentage: number | null; present: number | null; absent: number | null; classes: number | null }

const surface = 'rounded-lg border border-[#1e3348] bg-[linear-gradient(135deg,#0d1c2c_0%,#0b1826_100%)] shadow-[0_10px_24px_rgba(2,8,23,0.12)]'
const input = 'h-9 rounded-md border border-[#263d55] bg-[#091725] px-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-[#ffc72c] focus:ring-1 focus:ring-[#ffc72c]'
const PAGE_SIZE = 25

type GlyphName = 'search' | 'download' | 'plus' | 'upload' | 'more' | 'users' | 'calendar' | 'chart' | 'clock' | 'check' | 'alert' | 'close' | 'back'

const GLYPHS: Record<GlyphName, LucideIcon> = {
  search: Search,
  download: Download,
  plus: Plus,
  upload: Upload,
  more: Ellipsis,
  users: Users,
  calendar: CalendarDays,
  chart: BarChart3,
  clock: Clock3,
  check: Check,
  alert: AlertTriangle,
  close: X,
  back: ArrowLeft,
}

function Glyph({ name, size = 18 }: { name: GlyphName; size?: number }) {
  const Icon = GLYPHS[name]
  return <Icon aria-hidden="true" size={size} strokeWidth={1.8} />
}

function formatPercent(value: number | null) {
  return value === null || !Number.isFinite(value) ? '—' : `${value.toFixed(2)}%`
}

function importedStats(row: FacultyAttendanceRosterRow): ImportedStats {
  return {
    percentage: row.attendance_percentage ?? null,
    present: row.present ?? null,
    absent: row.absent ?? null,
    classes: row.record_count ?? null,
  }
}

function Stepper({ active, success = false }: { active: UploadStep; success?: boolean }) {
  const steps = ['Upload', 'Validate', 'Review', 'Import']
  return <div className="grid grid-cols-4 gap-2 border-b border-[#1e3348] pb-5">{steps.map((label, index) => { const number = (index + 1) as UploadStep; const complete = number < active || success; const current = number === active && !success; return <div key={label} className="relative text-center"><div className={`mx-auto flex h-7 w-7 items-center justify-center rounded-full border text-xs font-bold ${complete ? 'border-emerald-400 bg-emerald-500 text-[#06131f]' : current ? 'border-[#ffc72c] bg-[#ffc72c] text-[#111a21]' : 'border-[#506984] bg-[#102235] text-slate-400'}`}>{complete ? <Glyph name="check" size={14} /> : number}</div>{index < steps.length - 1 ? <span className={`absolute left-[58%] right-[-42%] top-3 h-px ${complete ? 'bg-emerald-400' : 'bg-[#30465c]'}`} /> : null}<p className={`mt-2 text-[11px] ${current ? 'font-semibold text-[#ffc72c]' : complete ? 'text-emerald-300' : 'text-slate-500'}`}>{label}</p></div> })}</div>
}

function EmptyAssignment() {
  return <section className={`${surface} flex min-h-[420px] flex-col items-center justify-center px-6 py-14 text-center`}><div className="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-[#17293d] text-[#ffc72c]"><GraduationCap aria-hidden="true" className="h-[42px] w-[42px]" strokeWidth={1.7} /></div><h2 className="text-xl font-bold text-white">No Active Assignments</h2><p className="mt-3 max-w-md text-sm leading-6 text-slate-400">You currently don't have any active course/section assignments. Once an administrator assigns you to a section, your attendance classes will appear here.</p></section>
}

type AttendanceActionRequest = { action: 'overview' | 'students' | 'mark' | 'upload' | 'history'; id: number }

export default function FacultyAttendance({
  accessToken,
  actionRequest,
  onNavigateAssignments,
  scopeVersion = '',
}: {
  accessToken: string
  actionRequest?: AttendanceActionRequest
  onNavigateAssignments?: () => void
  scopeVersion?: string
}) {
  const [assignments, setAssignments] = useState<FacultyAttendanceAssignment[]>([])
  const [assignmentId, setAssignmentId] = useState('')
  const [roster, setRoster] = useState<FacultyAttendanceRosterRow[]>([])
  const [overview, setOverview] = useState<AttendanceOverview | null>(null)
  const [sort, setSort] = useState('register_number')
  const [statuses, setStatuses] = useState<Record<string, AttendanceValue>>({})
  const [sessionDate, setSessionDate] = useState(() => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` })
  const [review, setReview] = useState<FacultyAttendanceImportReview | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [attendanceFilter, setAttendanceFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState<AttendanceTab>('students')
  const [profile, setProfile] = useState<FacultyAttendanceRosterRow | null>(null)
  const [markOpen, setMarkOpen] = useState(false)
  const [markPage, setMarkPage] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadStep, setUploadStep] = useState<UploadStep>(1)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [aiConfirmationFile, setAiConfirmationFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(true)
  const [rosterLoading, setRosterLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const selected = assignments.find((assignment) => assignment.assignment_id === assignmentId)
  const canManage = selected?.can_manage === true
  const scopeRef = useRef(selected?.section_id)
  scopeRef.current = selected?.section_id

  useEffect(() => {
    if (!actionRequest || actionRequest.id === 0) return
    if (actionRequest.action === 'upload') {
      setUploadOpen(true)
      setUploadStep(1)
      setUploadSuccess(false)
      setError(null)
    } else if (actionRequest.action === 'mark') {
      setMarkOpen(true)
    } else if (actionRequest.action === 'history') {
      setTab('history')
    } else {
      setTab('students')
    }
  }, [actionRequest])

  useEffect(() => {
    let current = true
    setLoading(true); setError(null)
    getFacultyAttendanceAssignments(accessToken).then((rows) => { if (current) { setAssignments(rows); setAssignmentId((previous) => rows.some((row) => row.assignment_id === previous) ? previous : rows[0]?.assignment_id || '') } }).catch(() => { if (current) { setAssignments([]); setRoster([]); setError('Unable to load attendance') } }).finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [accessToken, reloadKey, scopeVersion])

  useEffect(() => {
    if (!selected) { setRoster([]); setOverview(null); return }
    let current = true
    setRosterLoading(true); setError(null)
    setRoster([]); setOverview(null); setStatuses({}); setProfile(null)
    async function load() {
      const summary = await getFacultyAttendanceOverview(accessToken, selected!.section_id)
      const rows: FacultyAttendanceRosterRow[] = []
      while (current) {
        const result = await getFacultyAttendanceStudents(accessToken, selected!.section_id, new URLSearchParams({ limit: '500', offset: String(rows.length) }))
        rows.push(...result.items)
        if (rows.length >= result.total || result.items.length === 0) break
      }
      if (current) { setRoster(rows); setOverview(summary) }
    }
    void load().catch((cause: unknown) => { if (current) { setRoster([]); setError(cause instanceof Error ? cause.message : 'Unable to load attendance') } }).finally(() => { if (current) setRosterLoading(false) })
    return () => { current = false }
  }, [accessToken, selected?.section_id, reloadKey, scopeVersion])

  useEffect(() => { setStatuses({}); setMarkPage(0); setProfile(null); setMarkOpen(false); setUploadOpen(false); setReview(null); setPendingFile(null); setAiConfirmationFile(null) }, [selected?.section_id, scopeVersion, accessToken])
  useEffect(() => { const refresh = () => setReloadKey((key) => key + 1); window.addEventListener('focus', refresh); return () => window.removeEventListener('focus', refresh) }, [])

  const filteredRoster = useMemo(() => {
    const query = search.trim().toLowerCase()
    return roster.filter((row) => {
      const stats = importedStats(row)
      const matchesQuery = !query || [row.register_number, row.university_roll_number ?? '', row.student_name, row.email ?? ''].some((value) => value.toLowerCase().includes(query))
      const matchesStatus = statusFilter === 'all' || row.roster_status === statusFilter
      const matchesAttendance = attendanceFilter === 'all' || (attendanceFilter === 'low' ? stats.percentage !== null && stats.percentage < 75 : attendanceFilter === 'good' ? stats.percentage !== null && stats.percentage >= 75 : stats.percentage === null)
      return matchesQuery && matchesStatus && matchesAttendance
    }).sort((a, b) => sort === 'attendance' ? (a.attendance_percentage ?? -1) - (b.attendance_percentage ?? -1) : String(a[sort as 'register_number' | 'student_name']).localeCompare(String(b[sort as 'register_number' | 'student_name'])))
  }, [roster, search, statusFilter, attendanceFilter, sort])

  const totalPages = Math.max(1, Math.ceil(filteredRoster.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleRoster = filteredRoster.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  useEffect(() => {
    setPage(1)
  }, [assignmentId, search, statusFilter, attendanceFilter])

  const metrics = useMemo(() => {
    return { students: overview?.total_students ?? 0, average: overview?.average_attendance ?? null, low: overview?.low_attendance_count ?? 0, classes: overview?.session_count ?? null }
  }, [overview])

  function resetFilters() { setSearch(''); setStatusFilter('all'); setAttendanceFilter('all'); setPage(1) }

  function exportAttendance() {
    const escape = (value: string | number | null) => { const text = String(value ?? ''); return `"${(/^[\s]*[=+\-@]/.test(text) ? "'" : '') + text.replaceAll('"', '""')}"` }
    const csv = [['register_number', 'student_name', 'attendance_percentage', 'records'], ...filteredRoster.map((row) => [row.register_number, row.student_name, row.attendance_percentage ?? null, row.record_count ?? 0])].map((row) => row.map(escape).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'attendance.csv'; anchor.click(); URL.revokeObjectURL(url)
  }

  function onFileSelected(file: File | undefined) {
    if (!file) return
    if (file.size > 10 * 1024 * 1024) { setError('The file exceeds the 10 MB limit.'); return }
    const extension = file.name.toLowerCase().split('.').pop()
    if (!['csv', 'xls', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'webp'].includes(extension ?? '')) { setError('Choose a CSV, Excel, PDF, JPG, JPEG, PNG, or WEBP file.'); return }
    setPendingFile(file); setUploadStep(1); setUploadSuccess(false); setError(null)
  }

  async function processFile(file: File, aiConfirmed = false) {
    if (!selected || !canManage) return
    const expectedScope = selected.section_id
    setError(null); setMessage(null); setReview(null); setSaving(true); setUploadStep(2)
    try {
      const result = await uploadFacultyAttendance(accessToken, selected.section_id, selected.semester_id, file, aiConfirmed)
      if (scopeRef.current !== expectedScope) return
      setReview({ import_id: result.import_id, status: 'VALIDATED', summary: result.summary, rows: result.rows }); setPendingFile(null); setUploadStep(2)
    } catch (cause: unknown) {
      if (scopeRef.current !== expectedScope) return
      const code = cause && typeof cause === 'object' && 'code' in cause ? (cause as { code?: string }).code : undefined
      if (code === 'AI_CONFIRMATION_REQUIRED') { setAiConfirmationFile(file); setError('AI_CONFIRMATION_REQUIRED'); setUploadStep(1) } else { setError(cause instanceof Error ? cause.message : 'The file could not be processed. Check the format and try again.'); setUploadStep(1) }
    } finally { setSaving(false) }
  }

  async function saveAttendance() {
    if (!selected || !canManage || Object.keys(statuses).length === 0) return
    if (Object.keys(statuses).length > 500) { setError('Submit at most 500 marked students at a time.'); return }
    setSaving(true); setError(null); setMessage(null)
    try { const result = await markFacultyAttendance(accessToken, selected.section_id, sessionDate, statuses); setMessage(`${result.record_count} attendance records saved.`); setMarkOpen(false); setReloadKey((key) => key + 1) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Attendance could not be saved. Please try again.') } finally { setSaving(false) }
  }

  async function commit() {
    if (!review || !canManage) return
    setSaving(true); setError(null)
    try { await commitFacultyAttendanceImport(accessToken, review.import_id); setUploadStep(4); setUploadSuccess(true); setMessage('Attendance imported successfully.'); setReloadKey((key) => key + 1) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Import could not be committed. Please review the file and try again.') } finally { setSaving(false) }
  }

  function downloadValidationErrors() {
    if (!review) return
    const failedRows = review.rows.filter((row) => row.errors.length > 0)
    if (failedRows.length === 0) return
    const csv = [
      'row_number,register_number,student_name,errors',
      ...failedRows.map((row) => [
        row.row_number,
        row.normalized_data.register_number ?? '',
        row.normalized_data.student_name ?? '',
        row.errors.join('; '),
      ].map((value) => `"${( /^[\s]*[=+\-@]/.test(String(value)) ? "'" + String(value) : String(value)).replaceAll('"', '""')}"`).join(',')),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'attendance-validation-errors.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <div role="status" className="space-y-5"><div className="h-20 animate-pulse rounded-xl bg-[#102235]" /><div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{Array.from({ length: 6 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-xl bg-[#102235]" />)}</div><div className="h-96 animate-pulse rounded-xl bg-[#102235]" /></div>
  if (error === 'Unable to load attendance') return <section role="alert" className={`${surface} flex min-h-[360px] flex-col items-center justify-center px-6 text-center`}><div className="mb-4 rounded-full bg-red-500/10 p-4 text-red-300"><Glyph name="alert" size={28} /></div><h1 className="text-xl font-bold text-white">Unable to load attendance</h1><p className="mt-2 max-w-sm text-sm text-slate-400">We couldn't retrieve your attendance data. Please try again.</p><button type="button" onClick={() => setReloadKey((key) => key + 1)} className="mt-5 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d]">Try Again</button></section>

  return <section aria-label="Faculty Attendance" className="space-y-2">
    <div className="flex flex-col justify-between gap-3 xl:flex-row xl:items-end"><div><div className="mb-1 flex items-center gap-2 text-[10px] text-slate-400"><span>Attendance</span><span>›</span><span>{selected?.section.course.code ?? 'Assigned scope'}</span><span>›</span><span>{selected?.section.name ?? 'Select a section'}</span><span>›</span><span>{selected?.section.course.name}</span></div><h1 className="text-[26px] font-bold tracking-tight leading-7 text-white">Attendance</h1><p className="mt-1 text-xs text-slate-300">Manage attendance for your assigned courses and sections.</p></div><div className="flex gap-2"><label className="relative hidden md:block"><span className="sr-only">Search students, register number</span><span className="pointer-events-none absolute left-3 top-2 text-slate-500"><Glyph name="search" size={15} /></span><input className={`${input} h-[30px] w-[243px] pl-9 text-[11px]`} placeholder="Search students, register number..." value={search} onChange={(event) => setSearch(event.target.value)} /></label><button type="button" onClick={exportAttendance} className="inline-flex items-center gap-2 rounded-md border border-[#69551d] bg-[#1f1b10] px-3 py-1.5 text-[11px] font-semibold text-[#ffc72c] hover:bg-[#30270f]"><Glyph name="download" size={15} />Export <span aria-hidden="true">⌄</span></button></div></div>

    {assignments.length === 0 ? <EmptyAssignment /> : <>
      <div className={`${surface} grid gap-2.5 p-2 `}>
        <AttendanceAcademicFilters scopes={assignments} selectedId={assignmentId} onChange={setAssignmentId} />
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        <AttendanceMetric label="Total Students" value={metrics.students} icon="users" tone="yellow" />
        <AttendanceMetric label="Classes Conducted" value={metrics.classes} icon="calendar" tone="cyan" />
        <AttendanceMetric label="Average Attendance" value={metrics.average === null ? null : `${metrics.average.toFixed(1)}%`} icon="clock" tone="green" />
        <AttendanceMetric label="Total Present" value={overview?.present ?? null} icon="users" tone="blue" />
        <AttendanceMetric label="Total Absent" value={overview?.absent ?? null} icon="users" tone="red" />
        <AttendanceMetric label={<>Low Attendance <span className="block text-[10px] font-normal">(&lt; 75%)</span></>} value={metrics.low} icon="alert" tone="amber" />
      </div>

      {!canManage ? <p className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-200">Monitoring access. Marking and imports require an active teaching assignment and attendance permission for this subject.</p> : null}
      <p className="text-xs text-slate-500">75% is a monitoring threshold. Percentages use present / all recorded statuses. Imported summaries do not create attendance history.</p>
      <div className={`${surface} overflow-hidden`}>
        <div className="flex flex-col justify-between gap-2 border-b border-[#1e3348] px-2.5 pt-2 sm:flex-row sm:items-center sm:px-3"><div className="flex gap-1 overflow-x-auto">{([['students', 'Students', 'users'], ['history', 'Import History', 'clock'], ['sessions', 'Session-wise View', 'calendar'], ['reports', 'Reports', 'chart']] as const).map(([key, label, icon]) => <button key={key} type="button" onClick={() => setTab(key)} className={`inline-flex shrink-0 items-center gap-2 border-b-2 px-2.5 py-2.5 text-[11px] font-semibold ${tab === key ? 'border-[#ffc72c] text-[#ffc72c]' : 'border-transparent text-slate-400 hover:text-white'}`}><Glyph name={icon} size={14} />{label}</button>)}</div><div className="flex gap-2 pb-2 sm:pb-0"><button type="button" disabled={!canManage || saving} onClick={() => setMarkOpen(true)} className="inline-flex items-center gap-1.5 rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] hover:bg-[#ffd65d]"><Glyph name="plus" size={14} />Mark Attendance</button><button type="button" disabled={!canManage || saving} onClick={() => { setUploadOpen(true); setUploadStep(1); setUploadSuccess(false) }} className="inline-flex items-center gap-1.5 rounded-md bg-[#6538ed] px-3 py-1.5 text-[11px] font-bold text-white hover:bg-[#7d56ff]"><Glyph name="upload" size={14} />Upload Attendance</button></div></div>

        {tab !== 'students' && selected ? <AttendanceRecordedViews token={accessToken} sectionId={selected.section_id} view={tab} overview={overview} onReview={(id) => { setSaving(true); getFacultyAttendanceImportReview(accessToken, id).then((result) => { setReview(result); setUploadSuccess(false); setUploadOpen(true); setUploadStep(3) }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load import review')).finally(() => setSaving(false)) }} /> : <>
          <div className="flex flex-col gap-2 border-b border-[#1e3348] p-2 sm:flex-row sm:items-center sm:px-2.5"><label className="relative min-w-0 flex-1"><span className="sr-only">Search by name, register number or university roll number</span><span className="pointer-events-none absolute left-2.5 top-[7px] text-slate-500"><Glyph name="search" size={15} /></span><input className={`${input} h-[29px] w-full pl-8 text-[11px]`} placeholder="Search by name, register number or university roll number..." value={search} onChange={(event) => setSearch(event.target.value)} /></label><select aria-label="Filter by student status" className={`${input} h-[29px] w-full text-[11px] sm:w-[122px]`} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All Status</option><option value="ACTIVE">Active</option><option value="UNREGISTERED">Unregistered</option><option value="PENDING_APPROVAL">Pending Approval</option><option value="INACTIVE">Inactive</option></select><select aria-label="Filter by attendance" className={`${input} h-[29px] w-full text-[11px] sm:w-[155px]`} value={attendanceFilter} onChange={(event) => setAttendanceFilter(event.target.value)}><option value="all">All Attendance</option><option value="good">75% and above</option><option value="low">Below 75%</option><option value="unknown">Not available</option></select><button type="button" onClick={resetFilters} className="h-[29px] rounded-md border border-[#263d55] px-4 text-[11px] font-semibold text-slate-300 hover:bg-[#142638]">Reset</button></div>
          <label className="block p-2 text-xs text-slate-400">Sort students<select aria-label="Sort students" value={sort} onChange={(event) => setSort(event.target.value)} className={input}><option value="register_number">Register Number</option><option value="student_name">Student Name</option><option value="attendance">Attendance</option></select></label>
          {rosterLoading ? <div role="status" className="space-y-2 p-4">{Array.from({ length: 5 }, (_, index) => <div key={index} className="h-12 animate-pulse rounded bg-[#102235]" />)}</div> : filteredRoster.length === 0 ? <div className="p-12 text-center text-sm text-slate-400">No students match the current filters.</div> : <>
            <div className="overflow-x-auto"><table className="min-w-[920px] w-full text-left"><caption className="sr-only">Students attendance</caption><thead className="bg-[#0b1827] text-[10px] uppercase tracking-wide text-slate-400"><tr><th className="px-3 py-2 font-medium">#</th><th className="px-2.5 py-2 font-medium">Register Number</th><th className="px-2.5 py-2 font-medium">University Roll No.</th><th className="px-2.5 py-2 font-medium">Student Name</th><th className="px-2.5 py-2 font-medium">Email</th><th className="px-2.5 py-2 font-medium">Attendance ›</th><th className="px-2.5 py-2 font-medium">Registration / Monitoring</th><th className="px-2.5 py-2 font-medium">Actions</th></tr></thead><tbody>{visibleRoster.map((row, index) => { const stats = importedStats(row); return <tr key={row.roster_id} className="border-t border-[#1b3044] text-[11px] text-slate-300 transition-colors hover:bg-[#102235]"><td className="px-3 py-1.5 text-slate-500">{(currentPage - 1) * PAGE_SIZE + index + 1}</td><td className="px-2.5 py-1.5 font-medium text-slate-200">{row.register_number}</td><td className="px-2.5 py-1.5">{row.university_roll_number ?? '—'}</td><td className="px-2.5 py-1.5 font-medium text-white">{row.student_name}</td><td className="max-w-[170px] truncate px-2.5 py-1.5 text-slate-400">{row.email ?? '—'}</td><td className="px-2.5 py-1.5"><AttendanceMeter value={stats.percentage} /><span className="text-[10px] text-slate-500">{row.record_count ?? 0} records</span></td><td className="px-2.5 py-1.5"><AttendanceStatusBadge row={row} percentage={stats.percentage} /></td><td className="px-2.5 py-1.5"><div className="flex items-center gap-2"><button type="button" onClick={() => setProfile(row)} className="rounded-md border border-[#304862] px-3 py-1 text-[11px] font-semibold text-slate-200 hover:border-[#ffc72c] hover:text-[#ffc72c]">View</button></div></td></tr> })}</tbody></table></div>
            <div className="flex flex-col justify-between gap-3 border-t border-[#1e3348] px-4 py-2.5 text-xs text-slate-400 sm:flex-row sm:items-center"><span>Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredRoster.length)} of {filteredRoster.length} students</span><div className="flex items-center gap-1" aria-label="Attendance pagination"><button type="button" aria-label="Previous page" disabled={currentPage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="rounded p-1.5 text-slate-400 hover:bg-[#142638] hover:text-white disabled:cursor-not-allowed disabled:opacity-30">‹</button>{Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => <button key={pageNumber} type="button" aria-label={`Page ${pageNumber}`} aria-current={pageNumber === currentPage ? 'page' : undefined} onClick={() => setPage(pageNumber)} className={`min-w-7 rounded px-2 py-1.5 text-xs ${pageNumber === currentPage ? 'bg-[#1b2d43] font-semibold text-white' : 'text-slate-400 hover:bg-[#142638] hover:text-white'}`}>{pageNumber}</button>)}<button type="button" aria-label="Next page" disabled={currentPage === totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} className="rounded p-1.5 text-slate-400 hover:bg-[#142638] hover:text-white disabled:cursor-not-allowed disabled:opacity-30">›</button></div></div>
          </>}
        </>}
      </div>
    </>}

    {message ? <p role="status" className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</p> : null}
    {error && error !== 'Unable to load attendance' && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p> : null}
    {markOpen ? <Modal title="Mark Attendance" onClose={() => setMarkOpen(false)}>{selected && canManage ? <><p className="text-sm text-slate-400">Record attendance for {selected.section.course.name} · {selected.section.name}.</p><label className="mt-4 block text-xs font-semibold text-slate-300">Session date<input aria-label="Attendance date" type="date" value={sessionDate} onChange={(event) => setSessionDate(event.target.value)} className={`${input} mt-1 block w-full`} /></label><div className="mt-4 flex flex-wrap gap-2"><button type="button" onClick={() => setStatuses(Object.fromEntries(roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => [row.roster_id, 'present'])))} className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200">Mark all present</button><button type="button" onClick={() => setStatuses(Object.fromEntries(roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => [row.roster_id, 'absent'])))} className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200">Mark all absent</button></div><div className="mt-4 max-h-52 space-y-2 overflow-y-auto pr-1">{roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => <div key={row.roster_id} className="flex items-center justify-between gap-3 rounded-lg border border-[#1e3348] bg-[#091725] px-3 py-2"><span className="truncate text-xs text-slate-200">{row.student_name}<span className="ml-2 text-slate-500">{row.register_number}</span></span><select aria-label={`Attendance for ${row.student_name}`} value={statuses[row.roster_id] ?? ''} onChange={(event) => setStatuses((previous) => { const next = { ...previous }; if (event.target.value) next[row.roster_id] = event.target.value as AttendanceValue; else delete next[row.roster_id]; return next })} className="rounded border border-[#304862] bg-[#102235] px-2 py-1 text-xs text-white"><option value="">Not marked</option>{(['present', 'absent', 'late', 'excused'] as AttendanceValue[]).map((status) => <option key={status} value={status}>{status}</option>)}</select></div>)}</div><div className="mt-3 flex justify-between gap-2 text-xs text-slate-400"><span>Roster page {markPage + 1} ? up to 500 students per submission</span><button type="button" disabled={markPage === 0} onClick={() => { setStatuses({}); setMarkPage((value) => value - 1) }}>Previous roster page</button><button type="button" disabled={(markPage + 1) * 500 >= roster.length} onClick={() => { setStatuses({}); setMarkPage((value) => value + 1) }}>Next roster page</button></div><ModalActions onCancel={() => setMarkOpen(false)} submitLabel="Save Attendance" onSubmit={() => void saveAttendance()} saving={saving} /></> : <NoAssignmentWorkflow action="mark attendance" onNavigateAssignments={onNavigateAssignments} onClose={() => setMarkOpen(false)} />}</Modal> : null}
    {uploadOpen ? (
      <Modal title={uploadSuccess ? 'Import Complete' : 'Upload Attendance'} onClose={() => setUploadOpen(false)} wide>
        <Stepper active={uploadStep} success={uploadSuccess} />
        {uploadSuccess ? (
          <div className="py-10 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-[#06131f]"><Glyph name="check" size={30} /></div>
            <h2 className="mt-4 text-xl font-bold text-white">Attendance Imported Successfully</h2>
            <p className="mt-2 text-sm text-slate-400">{review?.summary.total_rows ?? review?.rows.length ?? 0} records processed. Invalid or conflicting records remain excluded.</p>
            <button type="button" onClick={() => { setUploadSuccess(false); setReview(null); setPendingFile(null); setAiConfirmationFile(null); setUploadStep(1) }} className="mt-6 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-bold text-[#101820]">Import Another File</button>
          </div>
        ) : assignments.length === 0 || (!canManage && !review) ? (
          <NoAssignmentWorkflow action="upload attendance" onNavigateAssignments={onNavigateAssignments} onClose={() => setUploadOpen(false)} />
        ) : uploadStep === 1 ? (
          <UploadFileStage
            dragging={dragging}
            pendingFile={pendingFile}
            aiConfirmationFile={aiConfirmationFile}
            saving={saving}
            error={error}
            onDraggingChange={setDragging}
            onFileSelected={onFileSelected}
            onRemoveFile={() => { setPendingFile(null); setAiConfirmationFile(null); setError(null) }}
            onCancelAi={() => { setAiConfirmationFile(null); setError(null) }}
            onProcess={(file, aiConfirmed) => void processFile(file, aiConfirmed)}
          />
        ) : uploadStep === 2 && saving ? (
          <div role="status" className="py-14 text-center">
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#ffc72c] border-t-transparent" />
            <p className="mt-4 text-sm text-slate-300">Validating your file…</p>
          </div>
        ) : uploadStep === 2 ? (
          <ValidationResultsStage
            review={review}
            onBack={() => { setUploadStep(1); setReview(null) }}
            onContinue={() => setUploadStep(3)}
            onDownloadErrors={downloadValidationErrors}
          />
        ) : (
          <ReviewImportStage
            review={review}
            saving={saving}
            readOnly={!canManage || review?.status === 'IMPORTED'}
            onCorrect={canManage && review?.status !== 'IMPORTED' ? (row, data) => { if (!review) return; setSaving(true); correctFacultyAttendanceImportRow(accessToken, review.import_id, row, data).then(setReview).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Correction failed')).finally(() => setSaving(false)) } : undefined}
            onBack={() => setUploadStep(2)}
            onCommit={() => void commit()}
            error={error}
          />
        )}
      </Modal>
    ) : null}
    {profile ? <Modal title="Student Attendance Profile" onClose={() => setProfile(null)}><button type="button" onClick={() => setProfile(null)} className="mb-4 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"><Glyph name="back" size={14} />Back to Students</button><div className="flex items-center gap-3"><div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#2a3d54] font-bold text-white">{profile.student_name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}</div><div><h2 className="font-bold text-white">{profile.student_name}</h2><p className="text-xs text-slate-400">{profile.register_number} · {profile.university_roll_number ?? 'No university roll number'}</p></div></div><div className="mt-4"><AttendanceStatusBadge row={profile} percentage={importedStats(profile).percentage} /></div><div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4"><ProfileStat label="Classes" value={importedStats(profile).classes} /><ProfileStat label="Present" value={importedStats(profile).present} /><ProfileStat label="Absent" value={importedStats(profile).absent} /><ProfileStat label="Attendance" value={formatPercent(importedStats(profile).percentage)} /></div><AttendanceStudentHistory token={accessToken} student={profile} /></Modal> : null}
  </section>
}

function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { const previous = document.activeElement as HTMLElement | null; ref.current?.focus(); return () => previous?.focus() }, [])
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title} onKeyDown={(event) => {
    if (event.key === 'Escape') onClose()
    if (event.key === 'Tab') { const nodes = ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary'); if (!nodes?.length) { event.preventDefault(); return } const first = nodes[0], last = nodes[nodes.length - 1]; if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { event.preventDefault(); last.focus() } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === ref.current)) { event.preventDefault(); first.focus() } }
  }} className={`max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-[#2c455e] bg-[#0d1c2c] p-5 shadow-2xl outline-none ${wide ? 'max-w-2xl' : 'max-w-lg'}`}><div className="flex items-center justify-between gap-4"><h2 className="text-lg font-bold text-white">{title}</h2><button type="button" aria-label={`Close ${title}`} onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-[#142638] hover:text-white"><Glyph name="close" /></button></div>{children}</div></div>
}

function NoAssignmentWorkflow({
  action,
  onNavigateAssignments,
  onClose,
}: {
  action: string
  onNavigateAssignments?: () => void
  onClose: () => void
}) {
  return (
    <div className="py-7 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#17293d] text-[#ffc72c]">
        <GraduationCap aria-hidden="true" size={28} strokeWidth={1.7} />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-white">No Active Assignments</h3>
      <p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-slate-400">
        You need an active course and section assignment before you can {action}. Ask your administrator to assign a section, then return here.
      </p>
      <div className="mt-4 flex justify-center gap-2">
        <button type="button" onClick={onClose} className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-[#142638]">Close</button>
        {onNavigateAssignments ? <button type="button" onClick={onNavigateAssignments} className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] hover:bg-[#ffd65d]">View My Sections</button> : null}
      </div>
    </div>
  )
}

function ModalActions({ onCancel, onSubmit, submitLabel, saving }: { onCancel: () => void; onSubmit: () => void; submitLabel: string; saving: boolean }) { return <div className="mt-5 flex justify-end gap-2 border-t border-[#1e3348] pt-4"><button type="button" onClick={onCancel} className="rounded-lg border border-[#2c455e] px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-[#142638]">Cancel</button><button type="button" disabled={saving} onClick={onSubmit} className="rounded-lg bg-[#ffc72c] px-4 py-2 text-xs font-bold text-[#101820] disabled:opacity-50">{saving ? 'Working…' : submitLabel}</button></div> }

function ProfileStat({ label, value }: { label: string; value: number | null | string }) { return <div className="rounded-lg border border-[#1e3348] bg-[#091725] p-3"><p className="text-lg font-bold text-white">{value === null ? '—' : value}</p><p className="mt-1 text-[10px] text-slate-500">{label}</p></div> }

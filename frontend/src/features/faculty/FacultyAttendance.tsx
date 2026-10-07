import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CalendarDays,
  Check,
  Cloud,
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
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceRoster,
  markFacultyAttendance,
  uploadFacultyAttendance,
  type FacultyAttendanceAssignment,
  type FacultyAttendanceImportReview,
  type FacultyAttendanceRosterRow,
} from '../../services/facultyAttendanceApi.ts'

type AttendanceValue = 'present' | 'absent' | 'late' | 'excused'
type UploadStep = 1 | 2 | 3 | 4
type AttendanceTab = 'students' | 'history' | 'sessions' | 'reports'
type ImportedStats = { percentage: number | null; present: number | null; absent: number | null; classes: number | null }

const surface = 'rounded-xl border border-[#1e3348] bg-[#0d1c2c]'
const input = 'rounded-lg border border-[#263d55] bg-[#091725] px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-[#ffc72c] focus:ring-1 focus:ring-[#ffc72c]'

type GlyphName = 'search' | 'download' | 'plus' | 'upload' | 'more' | 'users' | 'calendar' | 'chart' | 'clock' | 'check' | 'alert' | 'close' | 'back' | 'cloud'

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
  cloud: Cloud,
}

function Glyph({ name, size = 18 }: { name: GlyphName; size?: number }) {
  const Icon = GLYPHS[name]
  return <Icon aria-hidden="true" size={size} strokeWidth={1.8} />
}

function formatPercent(value: number | null) {
  return value === null || !Number.isFinite(value) ? '—' : `${value.toFixed(2)}%`
}

function importedStats(row: FacultyAttendanceRosterRow): ImportedStats {
  const raw = row.imported_summary
  if (!raw || typeof raw !== 'object') return { percentage: null, present: null, absent: null, classes: null }
  const number = (...keys: string[]) => {
    const value = keys.map((key) => raw[key]).find((candidate) => typeof candidate === 'number')
    return typeof value === 'number' && Number.isFinite(value) ? value : null
  }
  return {
    percentage: number('attendance_percentage', 'percentage', 'attendance'),
    present: number('present_classes', 'present'),
    absent: number('absent_classes', 'absent'),
    classes: number('total_classes', 'classes_conducted', 'classes'),
  }
}

function statusLabel(status: FacultyAttendanceRosterRow['roster_status']) {
  return { ACTIVE: 'Active', UNREGISTERED: 'Unregistered', PENDING_APPROVAL: 'Pending Approval', INACTIVE: 'Inactive' }[status]
}

function StatusBadge({ row, percentage }: { row: FacultyAttendanceRosterRow; percentage: number | null }) {
  const low = percentage !== null && percentage < 75
  const label = low ? 'Low Attendance' : statusLabel(row.roster_status)
  const tone = low || row.roster_status === 'INACTIVE' ? 'border-red-500/20 bg-red-500/10 text-red-300' : row.roster_status === 'ACTIVE' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/20 bg-amber-500/10 text-amber-300'
  return <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-semibold ${tone}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label}</span>
}

function AttendanceMeter({ value }: { value: number | null }) {
  const tone = value !== null && value < 75 ? 'bg-[#fb5364]' : value !== null && value < 85 ? 'bg-[#ffc43d]' : 'bg-[#16c992]'
  return <div className="flex min-w-[136px] items-center gap-2"><span className={`w-12 text-xs font-semibold ${value === null ? 'text-slate-500' : value < 75 ? 'text-red-300' : value < 85 ? 'text-amber-300' : 'text-emerald-300'}`}>{formatPercent(value)}</span><span className="h-1.5 w-20 overflow-hidden rounded-full bg-[#24384d]"><span className={`block h-full rounded-full ${tone}`} style={{ width: value === null ? '0%' : `${Math.max(0, Math.min(value, 100))}%` }} /></span></div>
}

function Stepper({ active, success = false }: { active: UploadStep; success?: boolean }) {
  const steps = ['Upload', 'Validate', 'Review', 'Import']
  return <div className="grid grid-cols-4 gap-2 border-b border-[#1e3348] pb-5">{steps.map((label, index) => { const number = (index + 1) as UploadStep; const complete = number < active || success; const current = number === active && !success; return <div key={label} className="relative text-center"><div className={`mx-auto flex h-7 w-7 items-center justify-center rounded-full border text-xs font-bold ${complete ? 'border-emerald-400 bg-emerald-500 text-[#06131f]' : current ? 'border-[#ffc72c] bg-[#ffc72c] text-[#111a21]' : 'border-[#506984] bg-[#102235] text-slate-400'}`}>{complete ? <Glyph name="check" size={14} /> : number}</div>{index < steps.length - 1 ? <span className={`absolute left-[58%] right-[-42%] top-3 h-px ${complete ? 'bg-emerald-400' : 'bg-[#30465c]'}`} /> : null}<p className={`mt-2 text-[11px] ${current ? 'font-semibold text-[#ffc72c]' : complete ? 'text-emerald-300' : 'text-slate-500'}`}>{label}</p></div> })}</div>
}

function EmptyAssignment() {
  return <section className={`${surface} flex min-h-[420px] flex-col items-center justify-center px-6 py-14 text-center`}><div className="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-[#17293d] text-[#ffc72c]"><GraduationCap aria-hidden="true" className="h-[42px] w-[42px]" strokeWidth={1.7} /></div><h2 className="text-xl font-bold text-white">No Active Assignments</h2><p className="mt-3 max-w-md text-sm leading-6 text-slate-400">You currently don't have any active course/section assignments. Once an administrator assigns you to a section, your attendance classes will appear here.</p></section>
}

export default function FacultyAttendance({ accessToken }: { accessToken: string }) {
  const [assignments, setAssignments] = useState<FacultyAttendanceAssignment[]>([])
  const [assignmentId, setAssignmentId] = useState('')
  const [roster, setRoster] = useState<FacultyAttendanceRosterRow[]>([])
  const [statuses, setStatuses] = useState<Record<string, AttendanceValue>>({})
  const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [review, setReview] = useState<FacultyAttendanceImportReview | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [attendanceFilter, setAttendanceFilter] = useState('all')
  const [tab, setTab] = useState<AttendanceTab>('students')
  const [profile, setProfile] = useState<FacultyAttendanceRosterRow | null>(null)
  const [markOpen, setMarkOpen] = useState(false)
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

  useEffect(() => {
    let current = true
    setLoading(true); setError(null)
    getFacultyAttendanceAssignments(accessToken).then((rows) => { if (current) { setAssignments(rows); setAssignmentId((previous) => previous || rows[0]?.assignment_id || '') } }).catch(() => { if (current) setError('Unable to load attendance') }).finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [accessToken, reloadKey])

  useEffect(() => {
    if (!selected) { setRoster([]); return }
    let current = true
    setRosterLoading(true); setError(null)
    getFacultyAttendanceRoster(accessToken, selected.section_id).then((rows) => { if (current) setRoster(rows) }).catch(() => { if (current) setError('Unable to load attendance') }).finally(() => { if (current) setRosterLoading(false) })
    return () => { current = false }
  }, [accessToken, selected?.section_id])

  const filteredRoster = useMemo(() => {
    const query = search.trim().toLowerCase()
    return roster.filter((row) => {
      const stats = importedStats(row)
      const matchesQuery = !query || [row.register_number, row.university_roll_number ?? '', row.student_name, row.email ?? ''].some((value) => value.toLowerCase().includes(query))
      const matchesStatus = statusFilter === 'all' || row.roster_status === statusFilter
      const matchesAttendance = attendanceFilter === 'all' || (attendanceFilter === 'low' ? stats.percentage !== null && stats.percentage < 75 : attendanceFilter === 'good' ? stats.percentage !== null && stats.percentage >= 75 : stats.percentage === null)
      return matchesQuery && matchesStatus && matchesAttendance
    })
  }, [roster, search, statusFilter, attendanceFilter])

  const metrics = useMemo(() => {
    const stats = roster.map(importedStats)
    const percentages = stats.map((item) => item.percentage).filter((item): item is number => item !== null)
    const classes = stats.map((item) => item.classes).filter((item): item is number => item !== null)
    return { students: roster.length, average: percentages.length ? percentages.reduce((sum, item) => sum + item, 0) / percentages.length : null, low: percentages.filter((item) => item < 75).length, classes: classes.length ? Math.max(...classes) : null }
  }, [roster])

  function resetFilters() { setSearch(''); setStatusFilter('all'); setAttendanceFilter('all') }

  function onFileSelected(file: File | undefined) {
    if (!file) return
    const extension = file.name.toLowerCase().split('.').pop()
    if (!['csv', 'xls', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'webp'].includes(extension ?? '')) { setError('Choose a CSV, Excel, PDF, JPG, JPEG, PNG, or WEBP file.'); return }
    setPendingFile(file); setUploadStep(1); setUploadSuccess(false); setError(null)
  }

  async function processFile(file: File, aiConfirmed = false) {
    if (!selected) return
    setError(null); setMessage(null); setSaving(true); setUploadStep(2)
    try {
      const result = await uploadFacultyAttendance(accessToken, selected.section_id, selected.semester_id, file, aiConfirmed)
      setReview({ import_id: result.import_id, status: 'VALIDATED', summary: result.summary, rows: result.rows }); setPendingFile(null); setUploadStep(3)
    } catch (cause: unknown) {
      const code = cause && typeof cause === 'object' && 'code' in cause ? (cause as { code?: string }).code : undefined
      if (code === 'AI_CONFIRMATION_REQUIRED') { setAiConfirmationFile(file); setError('AI_CONFIRMATION_REQUIRED'); setUploadStep(1) } else setError('The file could not be processed. Check the format and try again.')
    } finally { setSaving(false) }
  }

  async function saveAttendance() {
    if (!selected || Object.keys(statuses).length === 0) return
    setSaving(true); setError(null); setMessage(null)
    try { const result = await markFacultyAttendance(accessToken, selected.section_id, sessionDate, statuses); setMessage(`${result.record_count} attendance records saved.`); setMarkOpen(false) } catch { setError('Attendance could not be saved. Please try again.') } finally { setSaving(false) }
  }

  async function commit() {
    if (!review) return
    setSaving(true); setError(null)
    try { await commitFacultyAttendanceImport(accessToken, review.import_id); setUploadStep(4); setUploadSuccess(true); setMessage('Attendance imported successfully.'); if (selected) setRoster(await getFacultyAttendanceRoster(accessToken, selected.section_id)) } catch { setError('Import could not be committed. Please review the file and try again.') } finally { setSaving(false) }
  }

  if (loading) return <div role="status" className="space-y-5"><div className="h-20 animate-pulse rounded-xl bg-[#102235]" /><div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{Array.from({ length: 6 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-xl bg-[#102235]" />)}</div><div className="h-96 animate-pulse rounded-xl bg-[#102235]" /></div>
  if (error === 'Unable to load attendance') return <section role="alert" className={`${surface} flex min-h-[360px] flex-col items-center justify-center px-6 text-center`}><div className="mb-4 rounded-full bg-red-500/10 p-4 text-red-300"><Glyph name="alert" size={28} /></div><h1 className="text-xl font-bold text-white">Unable to load attendance</h1><p className="mt-2 max-w-sm text-sm text-slate-400">We couldn't retrieve your attendance data. Please try again.</p><button type="button" onClick={() => setReloadKey((key) => key + 1)} className="mt-5 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d]">Try Again</button></section>

  return <section aria-label="Faculty Attendance" className="space-y-5">
    <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end"><div><div className="mb-2 flex items-center gap-2 text-xs text-slate-500"><span>Attendance</span><span>›</span><span>{selected?.section.course.code ?? 'Assigned scope'}</span><span>›</span><span>{selected?.section.name ?? 'Select a section'}</span></div><h1 className="text-[30px] font-bold tracking-tight text-white">Attendance</h1><p className="mt-1 text-sm text-slate-400">Manage attendance for your assigned courses and sections.</p></div><div className="flex gap-2"><label className="relative hidden md:block"><span className="sr-only">Search students, register number</span><span className="pointer-events-none absolute left-3 top-2.5 text-slate-500"><Glyph name="search" size={16} /></span><input className={`${input} w-[260px] pl-9`} placeholder="Search students, register number..." value={search} onChange={(event) => setSearch(event.target.value)} /></label><button type="button" onClick={() => { const blob = new Blob([filteredRoster.map((row) => `${row.register_number},${row.student_name},${formatPercent(importedStats(row).percentage)}`).join('\n')], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'attendance.csv'; anchor.click(); URL.revokeObjectURL(url) }} className="inline-flex items-center gap-2 rounded-lg border border-[#69551d] bg-[#1f1b10] px-3 py-2 text-sm font-semibold text-[#ffc72c] hover:bg-[#30270f]"><Glyph name="download" size={16} />Export</button></div></div>

    {assignments.length === 0 ? <EmptyAssignment /> : <>
      <div className={`${surface} grid gap-3 p-3 sm:grid-cols-2 lg:grid-cols-4`}>
        <ScopeSelect label="Department / Program" value={selected ? `${selected.section.course.code} · ${selected.section.course.name}` : ''} options={assignments.map((item) => `${item.section.course.code} · ${item.section.course.name}`)} onChange={(value) => setAssignmentId(assignments.find((item) => `${item.section.course.code} · ${item.section.course.name}` === value)?.assignment_id ?? assignmentId)} />
        <ScopeSelect label="Semester" value={selected ? 'Assigned semester' : ''} options={['Assigned semester']} />
        <ScopeSelect label="Section" value={selected?.section.name ?? ''} options={assignments.map((item) => item.section.name)} onChange={(value) => setAssignmentId(assignments.find((item) => item.section.name === value)?.assignment_id ?? assignmentId)} />
        <ScopeSelect label="Subject / Course" value={selected ? `${selected.section.course.name} (${selected.section.course.code})` : ''} options={assignments.map((item) => `${item.section.course.name} (${item.section.course.code})`)} onChange={(value) => setAssignmentId(assignments.find((item) => `${item.section.course.name} (${item.section.course.code})` === value)?.assignment_id ?? assignmentId)} />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="Total Students" value={metrics.students} icon="users" tone="yellow" />
        <Metric label="Classes Conducted" value={metrics.classes} icon="calendar" tone="cyan" />
        <Metric label="Average Attendance" value={metrics.average === null ? null : formatPercent(metrics.average)} icon="clock" tone="green" />
        <Metric label="Present Today" value={null} icon="users" tone="blue" />
        <Metric label="Absent Today" value={null} icon="users" tone="red" />
        <Metric label={<>Low Attendance <span className="block text-[10px] font-normal">(&lt; 75%)</span></>} value={metrics.low} icon="alert" tone="amber" />
      </div>

      <div className={`${surface} overflow-hidden`}>
        <div className="flex flex-col justify-between gap-3 border-b border-[#1e3348] px-3 pt-3 sm:flex-row sm:items-center sm:px-4"><div className="flex gap-1 overflow-x-auto">{([['students', 'Students', 'users'], ['history', 'Attendance History', 'clock'], ['sessions', 'Session-wise View', 'calendar'], ['reports', 'Reports', 'chart']] as const).map(([key, label, icon]) => <button key={key} type="button" onClick={() => setTab(key)} className={`inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-xs font-semibold ${tab === key ? 'border-[#ffc72c] text-[#ffc72c]' : 'border-transparent text-slate-400 hover:text-white'}`}><Glyph name={icon} size={15} />{label}</button>)}</div><div className="flex gap-2 pb-3 sm:pb-0"><button type="button" onClick={() => setMarkOpen(true)} className="inline-flex items-center gap-1.5 rounded-lg bg-[#ffc72c] px-3 py-2 text-xs font-bold text-[#101820] hover:bg-[#ffd65d]"><Glyph name="plus" size={15} />Mark Attendance</button><button type="button" onClick={() => { setUploadOpen(true); setUploadStep(1); setUploadSuccess(false) }} className="inline-flex items-center gap-1.5 rounded-lg bg-[#6b3df5] px-3 py-2 text-xs font-bold text-white hover:bg-[#7d56ff]"><Glyph name="upload" size={15} />Upload Attendance</button><button type="button" aria-label="More attendance actions" className="rounded-lg border border-[#2b435b] px-2.5 text-slate-300 hover:bg-[#142638]"><Glyph name="more" size={18} /></button></div></div>

        {tab !== 'students' ? <div className="flex min-h-[260px] items-center justify-center px-6 text-center"><div><div className="mx-auto mb-3 w-fit rounded-full bg-[#162b42] p-4 text-slate-400"><Glyph name={tab === 'reports' ? 'chart' : tab === 'history' ? 'clock' : 'calendar'} size={25} /></div><h2 className="text-lg font-semibold text-white">{tab === 'history' ? 'Attendance History' : tab === 'sessions' ? 'Session-wise View' : 'Attendance Reports'}</h2><p className="mt-2 max-w-md text-sm text-slate-400">This view will show data from the attendance sessions available for the selected assignment.</p></div></div> : <>
          <div className="flex flex-col gap-2 border-b border-[#1e3348] p-3 sm:flex-row sm:items-center sm:px-4"><label className="relative min-w-0 flex-1"><span className="sr-only">Search by name, register number or university roll number</span><span className="pointer-events-none absolute left-3 top-2.5 text-slate-500"><Glyph name="search" size={16} /></span><input className={`${input} w-full pl-9`} placeholder="Search by name, register number or university roll number..." value={search} onChange={(event) => setSearch(event.target.value)} /></label><select aria-label="Filter by student status" className={input} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All Status</option><option value="ACTIVE">Active</option><option value="UNREGISTERED">Unregistered</option><option value="PENDING_APPROVAL">Pending Approval</option><option value="INACTIVE">Inactive</option></select><select aria-label="Filter by attendance" className={input} value={attendanceFilter} onChange={(event) => setAttendanceFilter(event.target.value)}><option value="all">All Attendance</option><option value="good">75% and above</option><option value="low">Below 75%</option><option value="unknown">Not available</option></select><button type="button" onClick={resetFilters} className="rounded-lg border border-[#263d55] px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-[#142638]">Reset</button></div>
          {rosterLoading ? <div role="status" className="space-y-2 p-4">{Array.from({ length: 5 }, (_, index) => <div key={index} className="h-12 animate-pulse rounded bg-[#102235]" />)}</div> : filteredRoster.length === 0 ? <div className="p-12 text-center text-sm text-slate-400">No students match the current filters.</div> : <>
            <div className="overflow-x-auto"><table className="min-w-[920px] w-full text-left"><caption className="sr-only">Students attendance</caption><thead className="bg-[#0b1827] text-[11px] uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3 font-medium">#</th><th className="px-3 py-3 font-medium">Register Number</th><th className="px-3 py-3 font-medium">University Roll No.</th><th className="px-3 py-3 font-medium">Student Name</th><th className="px-3 py-3 font-medium">Email</th><th className="px-3 py-3 font-medium">Attendance</th><th className="px-3 py-3 font-medium">Status</th><th className="px-3 py-3 font-medium">Actions</th></tr></thead><tbody>{filteredRoster.map((row, index) => { const stats = importedStats(row); return <tr key={row.roster_id} className="border-t border-[#1b3044] text-xs text-slate-300 hover:bg-[#102235]"><td className="px-4 py-3 text-slate-500">{index + 1}</td><td className="px-3 py-3 font-medium text-slate-200">{row.register_number}</td><td className="px-3 py-3">{row.university_roll_number ?? '—'}</td><td className="px-3 py-3 font-medium text-white">{row.student_name}</td><td className="max-w-[170px] truncate px-3 py-3 text-slate-400">{row.email ?? '—'}</td><td className="px-3 py-3"><AttendanceMeter value={stats.percentage} /></td><td className="px-3 py-3"><StatusBadge row={row} percentage={stats.percentage} /></td><td className="px-3 py-3"><div className="flex items-center gap-2"><button type="button" onClick={() => setProfile(row)} className="rounded-md border border-[#304862] px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-[#ffc72c] hover:text-[#ffc72c]">View</button><button type="button" aria-label={`More actions for ${row.student_name}`} className="rounded-md border border-[#304862] p-1.5 text-slate-400 hover:text-white"><Glyph name="more" size={15} /></button></div></td></tr> })}</tbody></table></div>
            <div className="flex flex-col justify-between gap-3 border-t border-[#1e3348] px-4 py-3 text-xs text-slate-400 sm:flex-row sm:items-center"><span>Showing 1–{filteredRoster.length} of {roster.length} students</span><span className="text-slate-500">Server scope is limited to your active assignment.</span></div>
          </>}
        </>}
      </div>
    </>}

    {message ? <p role="status" className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</p> : null}
    {error && error !== 'Unable to load attendance' && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p> : null}
    {markOpen && selected ? <Modal title="Mark Attendance" onClose={() => setMarkOpen(false)}><p className="text-sm text-slate-400">Record attendance for {selected.section.course.name} · {selected.section.name}.</p><label className="mt-4 block text-xs font-semibold text-slate-300">Session date<input aria-label="Attendance date" type="date" value={sessionDate} onChange={(event) => setSessionDate(event.target.value)} className={`${input} mt-1 block w-full`} /></label><div className="mt-4 flex flex-wrap gap-2"><button type="button" onClick={() => setStatuses(Object.fromEntries(roster.map((row) => [row.roster_id, 'present'])))} className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200">Mark all present</button><button type="button" onClick={() => setStatuses(Object.fromEntries(roster.map((row) => [row.roster_id, 'absent'])))} className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200">Mark all absent</button></div><div className="mt-4 max-h-52 space-y-2 overflow-y-auto pr-1">{roster.map((row) => <div key={row.roster_id} className="flex items-center justify-between gap-3 rounded-lg border border-[#1e3348] bg-[#091725] px-3 py-2"><span className="truncate text-xs text-slate-200">{row.student_name}<span className="ml-2 text-slate-500">{row.register_number}</span></span><select aria-label={`Attendance for ${row.student_name}`} value={statuses[row.roster_id] ?? ''} onChange={(event) => setStatuses((previous) => ({ ...previous, [row.roster_id]: event.target.value as AttendanceValue }))} className="rounded border border-[#304862] bg-[#102235] px-2 py-1 text-xs text-white"><option value="">Not marked</option>{(['present', 'absent', 'late', 'excused'] as AttendanceValue[]).map((status) => <option key={status} value={status}>{status}</option>)}</select></div>)}</div><ModalActions onCancel={() => setMarkOpen(false)} submitLabel="Save Attendance" onSubmit={() => void saveAttendance()} saving={saving} /></Modal> : null}
    {uploadOpen ? <Modal title={uploadSuccess ? 'Import Complete' : 'Upload Attendance'} onClose={() => setUploadOpen(false)} wide><Stepper active={uploadStep} success={uploadSuccess} />{uploadSuccess ? <div className="py-10 text-center"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-[#06131f]"><Glyph name="check" size={30} /></div><h2 className="mt-4 text-xl font-bold text-white">Attendance Imported Successfully</h2><p className="mt-2 text-sm text-slate-400">{review?.summary.total_rows ?? review?.rows.length ?? 0} records processed. Invalid or conflicting records remain excluded.</p><button type="button" onClick={() => { setUploadSuccess(false); setReview(null); setPendingFile(null); setAiConfirmationFile(null); setUploadStep(1) }} className="mt-6 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-bold text-[#101820]">Import Another File</button></div> : <>{uploadStep === 1 ? <div className="pt-5"><div onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); onFileSelected(event.dataTransfer.files[0]) }} className={`rounded-xl border border-dashed px-6 py-10 text-center ${dragging ? 'border-[#ffc72c] bg-[#ffc72c]/5' : 'border-[#3b5570] bg-[#0a1928]'}`}><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#1b3148] text-[#aac2df]"><Glyph name="cloud" size={28} /></div><h2 className="mt-4 font-semibold text-white">Upload Attendance File</h2><p className="mt-1 text-sm text-slate-400">Drag and drop your file here, or</p><label className="mt-4 inline-flex cursor-pointer items-center rounded-lg bg-[#ffc72c] px-4 py-2 text-xs font-bold text-[#101820] hover:bg-[#ffd65d]">Choose File<input aria-label="Attendance file" type="file" accept=".csv,.xls,.xlsx,.pdf,.png,.jpg,.jpeg,.webp" className="sr-only" onChange={(event) => onFileSelected(event.target.files?.[0])} /></label><p className="mt-4 text-xs text-[#ffc72c]">Recommended: Excel (.xlsx) or CSV (.csv)</p><p className="mt-1 text-[11px] text-slate-500">Also supported: PDF, JPG, JPEG, PNG, WEBP</p></div><div className="mt-4 rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-xs leading-5 text-blue-200">CSV and XLSX are parsed deterministically. No AI processing is required. PDF and image files may require OCR/AI processing and may consume AI tokens; you will be asked before processing.</div>{pendingFile ? <div className="mt-4 flex items-center justify-between rounded-lg border border-[#2b435b] bg-[#102235] px-3 py-2 text-xs"><span className="truncate text-slate-200">{pendingFile.name}</span><button type="button" onClick={() => { setPendingFile(null); setAiConfirmationFile(null); setError(null) }} aria-label="Remove selected file" className="text-slate-400 hover:text-white"><Glyph name="close" size={16} /></button></div> : null}{aiConfirmationFile ? <div role="alert" className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100"><p className="font-semibold">AI Processing May Be Required</p><p className="mt-1 text-xs text-amber-200/80">This file may require AI-assisted extraction. AI processing can consume tokens.</p><div className="mt-3 flex justify-end gap-2"><button type="button" className="rounded-lg border border-[#2c455e] px-3 py-2 text-xs" onClick={() => { setAiConfirmationFile(null); setError(null) }}>Cancel</button><button type="button" disabled={saving} className="rounded-lg bg-[#ffc72c] px-3 py-2 text-xs font-bold text-[#101820]" onClick={() => void processFile(aiConfirmationFile, true)}>Continue</button></div></div> : null}{!aiConfirmationFile ? <UploadModalError error={error} /> : null}{pendingFile && !aiConfirmationFile ? <ModalActions onCancel={() => setPendingFile(null)} submitLabel="Process File" onSubmit={() => void processFile(pendingFile, false)} saving={saving} /> : null}</div> : uploadStep === 2 ? <div role="status" className="py-14 text-center"><div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#ffc72c] border-t-transparent" /><p className="mt-4 text-sm text-slate-300">Validating your file…</p></div> : <ReviewImport review={review} saving={saving} onBack={() => { setUploadStep(1); setReview(null) }} onCommit={() => void commit()} error={error} />}</>}</Modal> : null}
    {profile ? <Modal title="Student Attendance Profile" onClose={() => setProfile(null)}><button type="button" onClick={() => setProfile(null)} className="mb-4 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"><Glyph name="back" size={14} />Back to Students</button><div className="flex items-center gap-3"><div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#2a3d54] font-bold text-white">{profile.student_name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}</div><div><h2 className="font-bold text-white">{profile.student_name}</h2><p className="text-xs text-slate-400">{profile.register_number} · {profile.university_roll_number ?? 'No university roll number'}</p></div></div><div className="mt-4"><StatusBadge row={profile} percentage={importedStats(profile).percentage} /></div><div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4"><ProfileStat label="Classes" value={importedStats(profile).classes} /><ProfileStat label="Present" value={importedStats(profile).present} /><ProfileStat label="Absent" value={importedStats(profile).absent} /><ProfileStat label="Attendance" value={formatPercent(importedStats(profile).percentage)} /></div><div className="mt-5 rounded-lg border border-[#1e3348] bg-[#091725] p-4"><h3 className="text-sm font-semibold text-white">Recent Attendance</h3><p className="mt-2 text-xs text-slate-500">Session history is not included in the current roster response.</p></div></Modal> : null}
  </section>
}

function ScopeSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange?: (value: string) => void }) { return <label className="block text-xs text-slate-400">{label}<select aria-label={label} className={`${input} mt-1 w-full`} value={value} onChange={(event) => onChange?.(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select></label> }

function Metric({ label, value, icon, tone }: { label: React.ReactNode; value: number | string | null; icon: 'users' | 'calendar' | 'clock' | 'alert'; tone: 'yellow' | 'cyan' | 'green' | 'blue' | 'red' | 'amber' }) { const colors = { yellow: 'bg-[#332a12] text-[#ffc72c]', cyan: 'bg-[#073640] text-[#20d5d2]', green: 'bg-[#063c34] text-[#23d29e]', blue: 'bg-[#102f59] text-[#4ca2ff]', red: 'bg-[#401c2a] text-[#fb5a6b]', amber: 'bg-[#3b2e13] text-[#ffc72c]' }; return <div className={`${surface} flex min-h-[96px] items-center gap-3 p-3`}><div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${colors[tone]}`}><Glyph name={icon} size={21} /></div><div className="min-w-0"><p className="text-xl font-bold text-white">{value === null ? '—' : value}</p><p className="text-[11px] leading-4 text-slate-400">{label}</p></div></div> }

function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) { return <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><div className={`max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-[#2c455e] bg-[#0d1c2c] p-5 shadow-2xl ${wide ? 'max-w-2xl' : 'max-w-lg'}`}><div className="flex items-center justify-between gap-4"><h2 className="text-lg font-bold text-white">{title}</h2><button type="button" aria-label={`Close ${title}`} onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-[#142638] hover:text-white"><Glyph name="close" /></button></div>{children}</div></div> }

function ModalActions({ onCancel, onSubmit, submitLabel, saving }: { onCancel: () => void; onSubmit: () => void; submitLabel: string; saving: boolean }) { return <div className="mt-5 flex justify-end gap-2 border-t border-[#1e3348] pt-4"><button type="button" onClick={onCancel} className="rounded-lg border border-[#2c455e] px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-[#142638]">Cancel</button><button type="button" disabled={saving} onClick={onSubmit} className="rounded-lg bg-[#ffc72c] px-4 py-2 text-xs font-bold text-[#101820] disabled:opacity-50">{saving ? 'Working…' : submitLabel}</button></div> }

function UploadModalError({ error }: { error: string | null }) { return error && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="mt-3 text-xs text-red-300">{error}</p> : error === 'AI_CONFIRMATION_REQUIRED' ? <div role="alert" className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100"><p className="font-semibold">AI Processing May Be Required</p><p className="mt-1 text-xs text-amber-200/80">This file may require AI-assisted extraction. AI processing can consume tokens.</p><div className="mt-3 flex justify-end gap-2"><button type="button" className="rounded-lg border border-[#2c455e] px-3 py-2 text-xs" onClick={() => window.dispatchEvent(new CustomEvent('faculty-upload-cancel-ai'))}>Cancel</button><span className="text-xs text-amber-200">Select Continue after confirming in the workflow.</span></div></div> : null }

function ReviewImport({ review, saving, onBack, onCommit, error }: { review: FacultyAttendanceImportReview | null; saving: boolean; onBack: () => void; onCommit: () => void; error: string | null }) { const summary = review?.summary ?? {}; const errors = Number(summary.errors ?? summary.ERROR ?? 0) + Number(summary.conflicts ?? summary.CONFLICT ?? 0); return <div className="pt-5"><div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-200"><span className="font-semibold">✓ File processed successfully</span><span className="ml-2 text-xs text-emerald-300/80">{summary.total_rows ?? review?.rows.length ?? 0} records detected</span></div><div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4"><ImportCount label="Valid Records" value={summary.valid ?? Number(summary.new_records ?? summary.NEW ?? 0) + Number(summary.updates ?? summary.UPDATE ?? 0)} tone="green" /><ImportCount label="New Records" value={summary.new_records ?? summary.NEW ?? 0} tone="blue" /><ImportCount label="Updates" value={summary.updates ?? summary.UPDATE ?? 0} tone="amber" /><ImportCount label="Errors" value={errors} tone="red" /></div>{errors > 0 ? <div className="mt-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-200"><span className="font-semibold">{errors} records have errors and cannot be imported.</span></div> : null}<div className="mt-4 max-h-56 overflow-auto rounded-lg border border-[#1e3348]"><table className="min-w-full text-left text-xs"><thead className="bg-[#0a1725] text-slate-500"><tr><th className="p-2">Row</th><th className="p-2">Student</th><th className="p-2">Status</th><th className="p-2">Issue</th></tr></thead><tbody>{review?.rows.map((row) => <tr key={row.row_number} className="border-t border-[#1e3348] text-slate-300"><td className="p-2">{row.row_number}</td><td className="p-2">{row.normalized_data.student_name ?? '—'}</td><td className="p-2">{row.validation_status}</td><td className="p-2 text-red-200">{row.errors.join('; ') || 'Ready for import'}</td></tr>)}</tbody></table></div>{error && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="mt-3 text-xs text-red-300">{error}</p> : null}<ModalActions onCancel={onBack} submitLabel={`Import ${Number(summary.valid ?? 0)} Valid Records`} onSubmit={onCommit} saving={saving} /></div> }

function ImportCount({ label, value, tone }: { label: string; value: number; tone: 'green' | 'blue' | 'amber' | 'red' }) { const colors = { green: 'text-emerald-300', blue: 'text-blue-300', amber: 'text-amber-300', red: 'text-red-300' }; return <div className="rounded-lg border border-[#1e3348] bg-[#091725] p-3"><p className={`text-lg font-bold ${colors[tone]}`}>{value}</p><p className="mt-1 text-[10px] text-slate-500">{label}</p></div> }

function ProfileStat({ label, value }: { label: string; value: number | null | string }) { return <div className="rounded-lg border border-[#1e3348] bg-[#091725] p-3"><p className="text-lg font-bold text-white">{value === null ? '—' : value}</p><p className="mt-1 text-[10px] text-slate-500">{label}</p></div> }

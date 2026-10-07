import { useEffect, useState } from 'react'
import { AttendanceMeter } from './AttendancePrimitives.tsx'
import {
  getFacultyAttendanceImports, getFacultyAttendanceProfile, getFacultyAttendanceSessions,
  type AttendanceImport, type AttendanceOverview, type AttendanceProfile, type AttendanceSession,
  type FacultyAttendanceAssignment, type FacultyAttendanceRosterRow,
} from '../../../services/facultyAttendanceApi.ts'

const input = 'mt-1 w-full rounded-md border border-[#263d55] bg-[#091725] p-2 text-xs text-slate-100 focus:ring-2 focus:ring-[#ffc72c]'
const button = 'rounded border border-[#304862] px-3 py-1.5 text-xs text-slate-200 disabled:opacity-30'

export function AttendanceAcademicFilters({ scopes, selectedId, onChange }: {
  scopes: FacultyAttendanceAssignment[]; selectedId: string; onChange: (id: string) => void
}) {
  const [filters, setFilters] = useState<Record<string, string>>({})
  useEffect(() => { setFilters({}) }, [scopes])
  const fields = [['department_id', 'Department', 'department'], ['program_id', 'Program', 'program'],
    ['academic_year_id', 'Academic Year', 'academic_year'], ['semester_id', 'Semester', 'semester'], ['code', 'Section/Class', 'section']] as const
  function matches(scope: FacultyAttendanceAssignment, values: Record<string, string>) {
    return Object.entries(values).every(([key, value]) => !value || String(scope.section[key as keyof typeof scope.section] ?? '') === value)
  }
  const available = scopes.filter((scope) => matches(scope, filters))
  return <div className="grid w-full gap-3 sm:grid-cols-2 lg:grid-cols-6">{fields.map(([key, label, entity], index) => {
    const parents = Object.fromEntries(fields.slice(0, index).map(([k]) => [k, filters[k] ?? '']))
    const options = new Map(scopes.filter((scope) => matches(scope, parents)).map((scope) => {
      const nested = entity === 'section' ? scope.section : scope.section[entity]
      return [String(scope.section[key] ?? ''), nested?.name ?? 'Unavailable']
    }))
    return <label key={key} className="min-w-0 text-xs text-slate-400">{label}<select className={input} aria-label={label} value={filters[key] ?? ''} onChange={(e) => {
      const next = { ...parents, [key]: e.target.value }; setFilters(next)
      onChange(scopes.find((s) => matches(s, next))?.assignment_id ?? '')
    }}><option value="">All authorized</option>{Array.from(options).filter(([id]) => id).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
  })}<label className="min-w-0 text-xs text-slate-400">Subject<select aria-label="Subject" className={input} value={selectedId} onChange={(e) => onChange(e.target.value)}>{available.map((scope) => <option key={scope.assignment_id} value={scope.assignment_id}>{scope.section.course.code} · {scope.section.course.name} · {scope.section.code}</option>)}</select></label></div>
}

export function AttendanceRecordedViews({ token, sectionId, view, overview, onReview }: {
  token: string; sectionId: string; view: 'history' | 'sessions' | 'reports'; overview: AttendanceOverview | null
  onReview: (id: string) => void
}) {
  const [sessions, setSessions] = useState<AttendanceSession[]>([])
  const [imports, setImports] = useState<AttendanceImport[]>([])
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setPage(0); setSessions([]); setImports([]) }, [sectionId, view])
  useEffect(() => {
    if (view === 'reports') return
    let live = true
    setLoading(true); setError('')
    const load = view === 'history'
      ? getFacultyAttendanceImports(token, sectionId, page * 50).then((rows) => { if (live) setImports(rows) })
      : getFacultyAttendanceSessions(token, sectionId, page * 50).then((result) => { if (live) setSessions(result.items) })
    load.catch((e: unknown) => { if (live) { setSessions([]); setImports([]); setError(e instanceof Error ? e.message : 'Attendance history could not be loaded') } }).finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [token, sectionId, view, page])
  const rows = view === 'history' ? imports : sessions
  return <div className="p-4"><h2 className="font-semibold text-white">{view === 'history' ? 'Import History' : view === 'sessions' ? 'Session-wise View' : 'Attendance Reports'}</h2>{error ? <p role="alert" className="mt-3 text-sm text-red-300">{error}</p> : null}{loading ? <p role="status" className="py-8 text-center text-slate-400">Loading history…</p> : view === 'reports' ? <><p className="mt-2 text-xs text-slate-400">Subject attendance trend · 75% monitoring threshold (not an eligibility policy).</p>{overview?.trend.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[500px] text-left text-xs"><thead><tr><th className="p-2">Date</th><th>Present</th><th>Absent</th><th>Records</th><th>Attendance</th></tr></thead><tbody>{overview.trend.slice(-30).map((row) => <tr className="border-t border-[#1e3348]" key={row.date}><td className="p-2">{row.date}</td><td>{row.present}</td><td>{row.absent}</td><td>{row.record_count}</td><td><AttendanceMeter value={row.attendance_percentage} /></td></tr>)}</tbody></table><p className="mt-3 text-xs text-slate-500">Most recent 30 dates; all sessions are available in Session-wise View.</p></div> : <p className="py-12 text-center text-sm text-slate-400">No recorded attendance data is available.</p>}</> : rows.length === 0 ? <p className="py-12 text-center text-sm text-slate-400">No {view === 'history' ? 'imports' : 'sessions'} are available for this subject.</p> : <div className="mt-4 overflow-x-auto">{view === 'history' ? <table className="w-full min-w-[900px] text-left text-xs"><thead><tr>{['Import ID / File', 'Uploaded by', 'Date/time', 'Rows', 'Imported', 'Rejected', 'Errors', 'Status', 'Review'].map((h) => <th key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{imports.map((row) => <tr className="border-t border-[#1e3348]" key={row.import_id}><td className="p-2">{row.original_filename}<p className="text-[10px] text-slate-500">{row.import_id}</p></td><td className="p-2">{row.uploaded_by}</td><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.summary.total_rows ?? 0}</td><td>{row.summary.imported ?? 0}</td><td>{row.summary.rejected ?? 0}</td><td>{(row.summary.errors ?? 0) + (row.summary.conflicts ?? 0) + (row.summary.duplicates ?? 0)}</td><td>{row.status}</td><td><button className={button} onClick={() => onReview(row.import_id)}>Review</button></td></tr>)}</tbody></table> : <table className="w-full min-w-[500px] text-left text-xs"><thead><tr>{['Date', 'Present', 'Absent', 'Records', 'Attendance'].map((h) => <th className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{sessions.map((row) => <tr key={row.session_id ?? row.session_date} className="border-t border-[#1e3348]"><td className="p-2">{row.session_date}</td><td>{row.present}</td><td>{row.absent}</td><td>{row.record_count}</td><td><AttendanceMeter value={row.attendance_percentage} /></td></tr>)}</tbody></table>}</div>}{view !== 'reports' ? <div className="mt-3 flex justify-end gap-2"><button className={button} disabled={page === 0} onClick={() => setPage(page - 1)}>Previous history page</button><span className="self-center text-xs text-slate-400">Page {page + 1}</span><button className={button} disabled={rows.length < 50} onClick={() => setPage(page + 1)}>Next history page</button></div> : null}</div>
}

export function AttendanceStudentHistory({ token, student }: { token: string; student: FacultyAttendanceRosterRow }) {
  const [profile, setProfile] = useState<AttendanceProfile | null>(null)
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  useEffect(() => {
    let live = true
    setProfile(null); setError('')
    getFacultyAttendanceProfile(token, student.roster_id, page * 50).then((result) => { if (live) setProfile(result) }).catch((e: unknown) => { if (live) setError(e instanceof Error ? e.message : 'Student history could not be loaded') })
    return () => { live = false }
  }, [token, student.roster_id, page])
  return <div className="mt-5 rounded-lg border border-[#1e3348] bg-[#091725] p-4"><h3 className="text-sm font-semibold text-white">Subject Attendance History</h3>{error ? <p role="alert" className="mt-3 text-xs text-red-300">{error}</p> : !profile ? <p role="status" className="mt-3 text-xs text-slate-400">Loading student history…</p> : <><p className="mt-2 text-xs text-slate-400">{profile.section.name} · {profile.section.course.name}. This percentage belongs to this subject only.</p>{profile.history.length ? <ul className="mt-3 divide-y divide-[#1e3348]">{profile.history.map((row) => <li key={row.record_id} className="flex justify-between py-2 text-xs text-slate-300"><span>{row.session_date}</span><span>{row.status}</span></li>)}</ul> : <p className="py-8 text-center text-sm text-slate-400">No attendance history for this subject.</p>}<div className="mt-3 flex justify-end gap-2"><button className={button} disabled={page === 0} onClick={() => setPage(page - 1)}>Previous student records</button><button className={button} disabled={(page + 1) * 50 >= profile.total} onClick={() => setPage(page + 1)}>Next student records</button></div></>}</div>
}

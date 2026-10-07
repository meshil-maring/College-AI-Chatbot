import { useState } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getFacultyResponsibilityReport } from '../../services/adminApi.ts'
import type { FacultyContext, FacultyResponsibility } from '../../types/faculty.ts'
import { visibleResponsibilities } from './responsibilities.ts'

function Report({ accessToken, responsibility }: { accessToken: string; responsibility: FacultyResponsibility }) {
  const [tab, setTab] = useState('Overview')
  const query = useApiQuery(['faculty', 'responsibility-report', accessToken, responsibility.responsibility_id], () => getFacultyResponsibilityReport(accessToken, responsibility.responsibility_id))
  const tabs = ['Overview', 'Courses & Sections', 'Students', 'Attendance', 'Low Attendance', 'Reports', ...(responsibility.permissions.includes('faculty.read') ? ['Faculty'] : [])]
  if (query.isPending) return <p role="status">Loading academic report…</p>
  if (query.isError) return <div role="alert"><p>{query.error instanceof Error ? query.error.message : 'This report is unavailable.'}</p><button type="button" onClick={() => void query.refetch()}>Retry report</button></div>
  if (!query.data) return null
  const report = query.data
  const students = tab === 'Low Attendance' ? report.low_attendance : report.students
  return <div className="space-y-4">
    <nav aria-label="Academic report views" className="flex flex-wrap gap-2">{tabs.map((label) => <button key={label} type="button" aria-current={tab === label ? 'page' : undefined} onClick={() => setTab(label)} className="rounded border border-slate-600 px-3 py-2">{label}</button>)}</nav>
    <h2 className="text-xl font-semibold">{tab}</h2>
    {tab === 'Overview' || tab === 'Reports' ? <div><p>{report.sections.length} subject sections · {report.students.length} subject roster entries · {report.session_count} recorded sessions</p><p className="mt-2 text-sm text-slate-400">Low attendance: below {report.low_attendance_threshold}%. Percentages use recorded sessions; students can appear once per subject. Imported summaries are excluded.</p></div> : null}
    {tab === 'Courses & Sections' ? <ul className="space-y-2">{report.sections.map((row) => <li key={row.section_id}>{row.course.name} — {row.program?.name} · {row.semester?.name} · Section {row.code}</li>)}</ul> : null}
    {tab === 'Students' || tab === 'Attendance' || tab === 'Low Attendance' ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Student</th><th className="p-2">Register number</th><th className="p-2">Subject / Section</th><th className="p-2">Recorded attendance</th></tr></thead><tbody>{students.map((row) => <tr key={row.roster_id}><td className="p-2">{row.student_name}</td><td className="p-2">{row.register_number}</td><td className="p-2">{report.sections.find((section) => section.section_id === row.section_id)?.course.name} · {report.sections.find((section) => section.section_id === row.section_id)?.code}</td><td className="p-2">{row.attendance_percentage === null ? 'No records' : `${row.attendance_percentage}% (${row.present_classes}/${row.total_classes})`}</td></tr>)}</tbody></table>{students.length === 0 ? <p className="mt-3">No students in this report.</p> : null}</div> : null}
    {tab === 'Faculty' ? <ul>{report.faculty.map((row) => <li key={row.id}>{row.first_name} {row.last_name}</li>)}{report.faculty.length === 0 ? <li>No active teaching faculty.</li> : null}</ul> : null}
  </div>
}

export default function FacultyResponsibilityWorkspace({ accessToken, context, permission }: { accessToken: string; context: FacultyContext; permission: string }) {
  const available = visibleResponsibilities(context).filter((row) => row.permissions.includes(permission))
  const [selected, setSelected] = useState('')
  const responsibility = available.find((row) => row.responsibility_id === selected) ?? available[0]
  if (!responsibility) return <p role="status">No active responsibility is available for this view.</p>
  return <section className="space-y-5 rounded-xl border border-slate-700 bg-slate-800 p-5">
    <h1 className="text-2xl font-semibold">{responsibility.name} — {responsibility.scope_label}</h1>
    {available.length > 1 ? <label>Academic scope<select value={responsibility.responsibility_id} onChange={(event) => setSelected(event.target.value)} className="ml-3 rounded bg-slate-900 p-2">{available.map((row) => <option key={row.responsibility_id} value={row.responsibility_id}>{row.scope_label}</option>)}</select></label> : null}
    <p className="text-sm text-slate-300">Academic monitoring. Manage subject attendance through your teaching assignments.</p>
    <Report key={`${responsibility.responsibility_id}:${responsibility.permissions.join(',')}:${responsibility.start_at}:${responsibility.end_at}`} accessToken={accessToken} responsibility={responsibility} />
  </section>
}

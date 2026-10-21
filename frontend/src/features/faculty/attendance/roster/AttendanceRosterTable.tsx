import { AttendanceMeter, AttendanceStatusBadge } from '../shared/AttendancePrimitives.tsx'
import { importedStats, PAGE_SIZE } from '../shared/AttendanceWorkspaceUi.tsx'
import type { FacultyAttendanceWorkspaceModel } from '../state/useAttendanceWorkspace.ts'
export function AttendanceRosterTable({ model }: { model: FacultyAttendanceWorkspaceModel }) {
  const { setProfile, currentPage, visibleRoster } = model
  return (
    <table className="min-w-[920px] w-full text-left">
      <caption className="sr-only">Students attendance</caption>
      <thead className="bg-[#0b1827] text-[10px] uppercase tracking-wide text-slate-400">
        <tr>
          <th className="px-3 py-2 font-medium">#</th>
          <th className="px-2.5 py-2 font-medium">Register Number</th>
          <th className="px-2.5 py-2 font-medium">University Roll No.</th>
          <th className="px-2.5 py-2 font-medium">Student Name</th>
          <th className="px-2.5 py-2 font-medium">Email</th>
          <th className="px-2.5 py-2 font-medium">Attendance ›</th>
          <th className="px-2.5 py-2 font-medium">Registration / Monitoring</th>
          <th className="px-2.5 py-2 font-medium">Actions</th>
        </tr>
      </thead>
      <tbody>
        {visibleRoster.map((row, index) => {
          const stats = importedStats(row)
          return (
            <tr
              key={row.roster_id}
              className="border-t border-[#1b3044] text-[11px] text-slate-300 transition-colors hover:bg-[#102235]"
            >
              <td className="px-3 py-1.5 text-slate-500">{(currentPage - 1) * PAGE_SIZE + index + 1}</td>
              <td className="px-2.5 py-1.5 font-medium text-slate-200">{row.register_number}</td>
              <td className="px-2.5 py-1.5">{row.university_roll_number ?? '—'}</td>
              <td className="px-2.5 py-1.5 font-medium text-white">{row.student_name}</td>
              <td className="max-w-[170px] truncate px-2.5 py-1.5 text-slate-400">{row.email ?? '—'}</td>
              <td className="px-2.5 py-1.5">
                <AttendanceMeter value={stats.percentage} />
                <span className="text-[10px] text-slate-500">{row.record_count ?? 0} records</span>
              </td>
              <td className="px-2.5 py-1.5">
                <AttendanceStatusBadge row={row} percentage={stats.percentage} />
              </td>
              <td className="px-2.5 py-1.5">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setProfile(row)}
                    className="rounded-md border border-[#304862] px-3 py-1 text-[11px] font-semibold text-slate-200 hover:border-[#ffc72c] hover:text-[#ffc72c]"
                  >
                    View
                  </button>
                </div>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

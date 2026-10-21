import type { StudentAttendanceRecord, StudentOwnAttendance } from '../../../types/student.ts'
import { NOT_PROVIDED } from '../shared/SectionState.tsx'
import { formatDate, formatLabel, formatPercent, formatText, isDisplayableNumber } from '../shared/studentFormat.ts'
export function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

/** Render a backend count safely — malformed values become the em dash. */
export function formatCount(value: unknown): string {
  return isDisplayableNumber(value) ? String(value) : NOT_PROVIDED
}

export function statusStyles(status: unknown): string {
  // Colour is decorative only — the status text itself is always rendered, so
  // no information is conveyed by colour alone.
  const value = typeof status === 'string' ? status.trim().toLowerCase() : ''
  if (value === 'present') return 'text-emerald-300'
  if (value === 'absent') return 'text-red-300'
  return 'text-slate-300'
}

export function SummaryFigures({ data }: { data: StudentOwnAttendance }) {
  const summary = data.summary
  return (
    <>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Figure label="Overall attendance" value={formatPercent(summary.attendance_percentage)} />
        <Figure label="Classes recorded" value={formatCount(summary.total_classes)} />
        <Figure label="Present" value={formatCount(summary.present_classes)} />
        <Figure label="Absent" value={formatCount(summary.absent_classes)} />
      </dl>
      {isDisplayableNumber(summary.late_classes) &&
      isDisplayableNumber(summary.excused_classes) &&
      (summary.late_classes > 0 || summary.excused_classes > 0) ? (
        <p className="mt-2 text-xs text-slate-400">
          Late: {summary.late_classes} · Excused: {summary.excused_classes}
        </p>
      ) : null}
    </>
  )
}

export function RecordsTable({ records }: { records: StudentAttendanceRecord[] }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[28rem] text-left text-sm">
        <caption className="sr-only">Your attendance records</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">
              Date
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Status
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Notes
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {records.map((record, index) => (
            <tr key={`${typeof record?.date === 'string' ? record.date : 'unknown'}-${index}`}>
              <td className="max-w-[10rem] truncate px-3 py-2 text-slate-200">
                {formatDate(typeof record?.date === 'string' ? record.date : null)}
              </td>
              <td className={`max-w-[8rem] truncate px-3 py-2 ${statusStyles(record?.status)}`}>
                {formatLabel(record?.status)}
              </td>
              <td className="max-w-[14rem] break-words px-3 py-2 text-slate-400">{formatText(record?.notes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

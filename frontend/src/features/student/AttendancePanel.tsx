/**
 * Phase 6.16 — Attendance summary.
 *
 * READ-ONLY by construction. The panel only ever calls
 * `GET /api/v1/students/me/attendance/summary`; there is no attendance-marking
 * control anywhere in the student experience and the backend exposes no
 * student write path for attendance. Marking attendance stays an administrator
 * action (`/api/v1/admin/attendance`), which a student receives 403 for.
 *
 * Every number displayed is computed by the backend (`total_classes`,
 * `present_classes`, `absent_classes`, `late_classes`, `excused_classes`,
 * `attendance_percentage`); the frontend performs no attendance arithmetic.
 *
 * `compact` renders the dashboard card (key figures + the most recent days);
 * without it the full Attendance page table is rendered.
 */

import type { StudentOwnAttendance } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED } from './SectionState.tsx'
import { formatDate, formatLabel, formatPercent } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No attendance records are available yet.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

function statusStyles(status: string | null): string {
  // Colour is decorative only — the status text itself is always rendered, so
  // no information is conveyed by colour alone.
  const value = (status ?? '').trim().toLowerCase()
  if (value === 'present') return 'text-emerald-300'
  if (value === 'absent') return 'text-red-300'
  return 'text-slate-300'
}

export default function AttendancePanel({
  attendance,
  compact = false,
}: {
  attendance: StudentResourceState<StudentOwnAttendance>
  compact?: boolean
}) {
  if (attendance.status === 'loading' || attendance.status === 'idle') {
    return <LoadingBlock label="Loading your attendance…" />
  }

  if (attendance.status === 'error') {
    return (
      <ErrorBlock
        message={attendance.error ?? 'Unable to load attendance.'}
        onRetry={attendance.reload}
      />
    )
  }

  const data = attendance.data
  if (data === null || !data.summary.records_available || data.records.length === 0) {
    return <EmptyBlock message={EMPTY_MESSAGE} />
  }

  const summary = data.summary
  const rows = compact ? data.records.slice(0, 5) : data.records

  return (
    <>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Figure label="Overall attendance" value={formatPercent(summary.attendance_percentage)} />
        <Figure label="Classes recorded" value={String(summary.total_classes)} />
        <Figure label="Present" value={String(summary.present_classes)} />
        <Figure label="Absent" value={String(summary.absent_classes)} />
      </dl>

      {summary.late_classes > 0 || summary.excused_classes > 0 ? (
        <p className="mt-2 text-xs text-slate-400">
          Late: {summary.late_classes} · Excused: {summary.excused_classes}
        </p>
      ) : null}

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full text-left text-sm">
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
            {rows.map((record, index) => (
              <tr key={`${record.date ?? 'unknown'}-${index}`}>
                <td className="px-3 py-2 text-slate-200">{formatDate(record.date)}</td>
                <td className={`px-3 py-2 ${statusStyles(record.status)}`}>
                  {formatLabel(record.status)}
                </td>
                <td className="px-3 py-2 text-slate-400">{record.notes?.trim() || NOT_PROVIDED}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {compact && data.records.length > rows.length ? (
        <p className="mt-2 text-xs text-slate-500">
          Showing the {rows.length} most recent of {data.records.length} records.
        </p>
      ) : null}
    </>
  )
}

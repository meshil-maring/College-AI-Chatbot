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
import { formatDate, formatLabel, formatPercent, formatText, isDisplayableNumber } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No attendance records are available yet.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

function statusStyles(status: unknown): string {
  // Colour is decorative only — the status text itself is always rendered, so
  // no information is conveyed by colour alone.
  const value = typeof status === 'string' ? status.trim().toLowerCase() : ''
  if (value === 'present') return 'text-emerald-300'
  if (value === 'absent') return 'text-red-300'
  return 'text-slate-300'
}

/** Render a backend count safely — malformed values become the em dash. */
function formatCount(value: unknown): string {
  return isDisplayableNumber(value) ? String(value) : NOT_PROVIDED
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
  if (data === null || data === undefined || typeof data !== 'object') {
    return <EmptyBlock message={EMPTY_MESSAGE} />
  }
  const summary = (data as StudentOwnAttendance).summary
  const rawRecords = (data as StudentOwnAttendance).records
  const records = Array.isArray(rawRecords) ? rawRecords : []
  if (
    summary === null ||
    summary === undefined ||
    typeof summary !== 'object' ||
    (summary as { records_available?: unknown }).records_available !== true ||
    records.length === 0
  ) {
    return <EmptyBlock message={EMPTY_MESSAGE} />
  }
  const typedSummary = summary as StudentOwnAttendance['summary']
  const rows = records

  return (
    <>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Figure label="Overall attendance" value={formatPercent(typedSummary.attendance_percentage)} />
        <Figure label="Classes recorded" value={formatCount(typedSummary.total_classes)} />
        <Figure label="Present" value={formatCount(typedSummary.present_classes)} />
        <Figure label="Absent" value={formatCount(typedSummary.absent_classes)} />
      </dl>

      {isDisplayableNumber(typedSummary.late_classes) &&
      isDisplayableNumber(typedSummary.excused_classes) &&
      (typedSummary.late_classes > 0 || typedSummary.excused_classes > 0) ? (
        <p className="mt-2 text-xs text-slate-400">
          Late: {typedSummary.late_classes} · Excused: {typedSummary.excused_classes}
        </p>
      ) : null}

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
            {rows.map((record, index) => (
              <tr key={`${typeof record?.date === 'string' ? record.date : 'unknown'}-${index}`}>
                <td className="max-w-[10rem] truncate px-3 py-2 text-slate-200">
                  {formatDate(typeof record?.date === 'string' ? record.date : null)}
                </td>
                <td className={`max-w-[8rem] truncate px-3 py-2 ${statusStyles(record?.status)}`}>
                  {formatLabel(record?.status)}
                </td>
                <td className="max-w-[14rem] truncate px-3 py-2 text-slate-400">
                  {formatText(record?.notes)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {compact && records.length > rows.length ? (
        <p className="mt-2 text-xs text-slate-500">
          Showing the {rows.length} most recent of {records.length} records.
        </p>
      ) : null}
    </>
  )
}

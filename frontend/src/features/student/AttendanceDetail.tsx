/**
 * Phase 6.16.2 — Student attendance DETAIL experience (read-only).
 *
 * Page flow:  Dashboard → Attendance overview → this page.
 *
 * Layout (per phase spec):
 *
 *   Attendance
 *   ────────────────────────────
 *   Academic context      <- existing /me/academic-profile contract
 *   Overall summary       <- server-computed figures, displayed verbatim
 *   Filters               <- server-side date range (date_from / date_to only)
 *   Attendance records    <- student-safe rows (date / status / notes)
 *
 * Read-only by construction: the page only ever GETs the existing
 * `/students/me/attendance/summary` and `/students/me/academic-profile`
 * contracts. There is no marking/editing control anywhere and no student
 * write path exists in the backend.
 *
 * No frontend attendance arithmetic: the percentage and every count shown are
 * the backend's values (`attendance_percentage`, `total_classes`, ...). An
 * empty state NEVER implies zero attendance — it says records are "not
 * available" for the selection, because a filtered request legitimately
 * returns nothing.
 *
 * Filter decision (documented in the phase report): the endpoint also supports
 * `academic_year_id` / `semester_id`, but NO student-accessible contract
 * exposes those IDs (the academic profile returns names/codes only), so the UI
 * offers the date-range filter only and never invents identifiers or performs
 * frontend-only filtering. The 200-record page size is a SERVER cap — the
 * client cannot raise it because the contract has no `limit` query field.
 */

import { useState } from 'react'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  type StudentAttendanceFilters,
} from '../../services/studentApi.ts'
import type { StudentAttendanceRecord, StudentOwnAttendance } from '../../types/student.ts'
import { useStudentResource, type StudentResourceState } from './useStudentResource.ts'
import AcademicContextCard from './AcademicContextCard.tsx'
import { EmptyBlock, ErrorBlock, LoadingBlock, SectionCard, NOT_PROVIDED } from './SectionState.tsx'
import {
  formatDate,
  formatLabel,
  formatPercent,
  formatText,
  isDisplayableNumber,
} from './studentFormat.ts'

/** Server-enforced page size of `GET /students/me/attendance/summary`. */
const SERVER_RECORD_LIMIT = 200

const EMPTY_ALL_MESSAGE = 'No attendance records are available yet.'
const EMPTY_FILTERED_MESSAGE = 'No attendance records are available for this selection.'
const LOAD_ERROR_MESSAGE = 'Unable to load attendance.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

/** Render a backend count safely — malformed values become the em dash. */
function formatCount(value: unknown): string {
  return isDisplayableNumber(value) ? String(value) : NOT_PROVIDED
}

function statusStyles(status: unknown): string {
  // Colour is decorative only — the status text itself is always rendered, so
  // no information is conveyed by colour alone.
  const value = typeof status === 'string' ? status.trim().toLowerCase() : ''
  if (value === 'present') return 'text-emerald-300'
  if (value === 'absent') return 'text-red-300'
  return 'text-slate-300'
}

function SummaryFigures({ data }: { data: StudentOwnAttendance }) {
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

function RecordsTable({ records }: { records: StudentAttendanceRecord[] }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[28rem] text-left text-sm">
        <caption className="sr-only">Your attendance records</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">Date</th>
            <th scope="col" className="px-3 py-2 font-medium">Status</th>
            <th scope="col" className="px-3 py-2 font-medium">Notes</th>
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
              <td className="max-w-[14rem] break-words px-3 py-2 text-slate-400">
                {formatText(record?.notes)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Server-side date-range filter form. Values are sent to the backend as
 * `date_from` / `date_to`; the SERVER validates them (422 INVALID_FILTER) and
 * remains authoritative — the UI never narrows data locally. Date-range
 * filtering is not security-sensitive: the endpoint always scopes rows to the
 * authenticated student's own records first.
 */
function AttendanceFilterForm({
  fromDraft,
  toDraft,
  onFromChange,
  onToChange,
  onApply,
  onReset,
}: {
  fromDraft: string
  toDraft: string
  onFromChange: (value: string) => void
  onToChange: (value: string) => void
  onApply: () => void
  onReset: () => void
}) {
  return (
    <form
      className="mt-4 rounded-lg border border-slate-700 bg-slate-900/40 p-3"
      aria-label="Attendance date filter"
      onSubmit={(event) => {
        event.preventDefault()
        onApply()
      }}
    >
      <p className="text-xs text-slate-400">
        Narrow your own attendance by date. The server applies this filter to your records.
      </p>
      <div className="mt-2 flex flex-wrap items-end gap-3">
        <div className="min-w-[9rem]">
          <label htmlFor="attendance-filter-from" className="block text-xs font-medium text-slate-300">
            From date
          </label>
          <input
            id="attendance-filter-from"
            type="date"
            value={fromDraft}
            onChange={(event) => onFromChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
        </div>
        <div className="min-w-[9rem]">
          <label htmlFor="attendance-filter-to" className="block text-xs font-medium text-slate-300">
            To date
          </label>
          <input
            id="attendance-filter-to"
            type="date"
            value={toDraft}
            onChange={(event) => onToChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Apply date filter
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Reset filter
        </button>
      </div>
    </form>
  )
}

function AttendanceDetailBody({
  attendance,
  filtersActive,
  fromDraft,
  toDraft,
  onFromChange,
  onToChange,
  onApply,
  onReset,
}: {
  attendance: StudentResourceState<StudentOwnAttendance>
  filtersActive: boolean
  fromDraft: string
  toDraft: string
  onFromChange: (value: string) => void
  onToChange: (value: string) => void
  onApply: () => void
  onReset: () => void
}) {
  const data = attendance.data
  if (data === null || data === undefined || typeof data !== 'object') {
    return <EmptyBlock message={EMPTY_ALL_MESSAGE} />
  }
  const rawRecords = data.records
  const records = Array.isArray(rawRecords) ? rawRecords : []
  const form = (
    <AttendanceFilterForm
      fromDraft={fromDraft}
      toDraft={toDraft}
      onFromChange={onFromChange}
      onToChange={onToChange}
      onApply={onApply}
      onReset={onReset}
    />
  )
  if (data.summary?.records_available !== true || records.length === 0) {
    // Never implies zero attendance — records are simply not available for
    // this selection (newly approved student, no rows yet, or an empty filter).
    return (
      <>
        {form}
        <div className="mt-3">
          <EmptyBlock message={filtersActive ? EMPTY_FILTERED_MESSAGE : EMPTY_ALL_MESSAGE} />
        </div>
      </>
    )
  }
  return (
    <>
      <SummaryFigures data={data} />
      {form}
      <RecordsTable records={records} />
      {records.length >= SERVER_RECORD_LIMIT ? (
        <p className="mt-2 text-xs text-slate-500">
          Showing the {records.length} most recent attendance records held on the server. Use the
          date filter to narrow this list.
        </p>
      ) : null}
    </>
  )
}

export function AttendanceDetailPage() {
  const profile = useStudentResource(getMyAcademicProfile, 'Unable to load your academic context.')
  const [filters, setFilters] = useState<StudentAttendanceFilters>({})
  const [fromDraft, setFromDraft] = useState('')
  const [toDraft, setToDraft] = useState('')

  // One serialized key per filter selection: changing it reloads the resource
  // with exactly ONE new request (see useStudentResource watchKey).
  const watchKey = `${filters.dateFrom ?? ''}|${filters.dateTo ?? ''}`
  const attendance = useStudentResource(
    (token) => getMyAttendanceSummary(token, filters),
    LOAD_ERROR_MESSAGE,
    watchKey,
  )

  const filtersActive = filters.dateFrom !== undefined || filters.dateTo !== undefined

  return (
    <div className="min-w-0 space-y-4 overflow-x-clip">
      <SectionCard title="Academic context" headingId="student-attendance-context">
        <AcademicContextCard profile={profile} />
      </SectionCard>

      <SectionCard title="Your attendance" headingId="student-attendance-detail">
        {attendance.status === 'loading' || attendance.status === 'idle' ? (
          <LoadingBlock label="Loading your attendance…" />
        ) : attendance.status === 'error' ? (
          <ErrorBlock message={attendance.error ?? LOAD_ERROR_MESSAGE} onRetry={attendance.reload} />
        ) : (
          <AttendanceDetailBody
            attendance={attendance}
            filtersActive={filtersActive}
            fromDraft={fromDraft}
            toDraft={toDraft}
            onFromChange={setFromDraft}
            onToChange={setToDraft}
            onApply={() => {
              setFilters({
                dateFrom: fromDraft.trim() === '' ? undefined : fromDraft.trim(),
                dateTo: toDraft.trim() === '' ? undefined : toDraft.trim(),
              })
            }}
            onReset={() => {
              setFromDraft('')
              setToDraft('')
              setFilters({})
            }}
          />
        )}
      </SectionCard>
    </div>
  )
}
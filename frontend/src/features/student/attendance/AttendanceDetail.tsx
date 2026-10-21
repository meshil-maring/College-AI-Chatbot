import { useState } from 'react'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  type StudentAttendanceFilters,
} from '../../../services/students/studentApi.ts'
import type { StudentOwnAttendance } from '../../../types/student.ts'
import AcademicContextCard from '../shared/AcademicContextCard.tsx'
import { AttendanceFilterForm } from './AttendanceFilterForm.tsx'
import { RecordsTable, SummaryFigures } from './AttendanceRecords.tsx'
import { EmptyBlock, ErrorBlock, LoadingBlock, SectionCard } from '../shared/SectionState.tsx'
import { useStudentResource, type StudentResourceState } from '../shared/useStudentResource.ts'
/** Server-enforced page size of `GET /students/me/attendance/summary`. */
const SERVER_RECORD_LIMIT = 200

const EMPTY_ALL_MESSAGE = 'No attendance records are available yet.'

const EMPTY_FILTERED_MESSAGE = 'No attendance records are available for this selection.'

const LOAD_ERROR_MESSAGE = 'Unable to load attendance.'

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
          Showing the {records.length} most recent attendance records held on the server. Use the date filter to narrow
          this list.
        </p>
      ) : null}
    </>
  )
}

export function AttendanceDetailPage() {
  const profile = useStudentResource(
    getMyAcademicProfile,
    'Unable to load your academic context.',
    '',
    'academic-profile',
  )
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
    'attendance-detail',
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

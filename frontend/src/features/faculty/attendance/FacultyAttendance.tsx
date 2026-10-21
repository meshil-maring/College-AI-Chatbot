import { AttendanceMetric } from './shared/AttendancePrimitives.tsx'
import { AttendanceProfileDialog } from './dialogs/AttendanceProfileDialog.tsx'
import { AttendanceAcademicFilters } from './roster/AttendanceRecordedViews.tsx'
import { AttendanceRoster } from './roster/AttendanceRoster.tsx'
import { AttendanceUploadDialog } from './dialogs/AttendanceUploadDialog.tsx'
import { EmptyAssignment, Glyph, input, surface } from './shared/AttendanceWorkspaceUi.tsx'
import { MarkAttendanceDialog } from './dialogs/MarkAttendanceDialog.tsx'
import { useAttendanceWorkspace } from './state/useAttendanceWorkspace.ts'
import { type FacultyAttendanceProps } from './state/workspaceTypes.ts'

function FacultyAttendanceWorkspace(props: Parameters<typeof useAttendanceWorkspace>[0]) {
  const model = useAttendanceWorkspace(props)
  const {
    setAssignmentId,
    search,
    setSearch,
    message,
    error,
    assignments,
    selected,
    overview,
    assignmentsQuery,
    overviewQuery,
    sectionUnavailable,
    rosterIncomplete,
    retry,
    loadError,
    refreshing,
    canManage,
    metrics,
    exportAttendance,
  } = model

  if (assignmentsQuery.isPending)
    return (
      <div role="status" className="space-y-5">
        <div className="h-20 animate-pulse rounded-xl bg-[#102235]" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-xl bg-[#102235]" />
          ))}
        </div>
        <div className="h-96 animate-pulse rounded-xl bg-[#102235]" />
      </div>
    )
  if (assignmentsQuery.isError)
    return (
      <section
        role="alert"
        className={`${surface} flex min-h-[360px] flex-col items-center justify-center px-6 text-center`}
      >
        <div className="mb-4 rounded-full bg-red-500/10 p-4 text-red-300">
          <Glyph name="alert" size={28} />
        </div>
        <h1 className="text-xl font-bold text-white">Unable to load attendance</h1>
        <p className="mt-2 max-w-sm text-sm text-slate-400">
          We couldn't retrieve your attendance data. Please try again.
        </p>
        <button
          type="button"
          onClick={() => void retry()}
          className="mt-5 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d]"
        >
          Try Again
        </button>
      </section>
    )

  return (
    <section aria-label="Faculty Attendance" className="space-y-2">
      <div className="flex flex-col justify-between gap-3 xl:flex-row xl:items-end">
        <div>
          <div className="mb-1 flex items-center gap-2 text-[10px] text-slate-400">
            <span>Attendance</span>
            <span>›</span>
            <span>{selected?.section.course.code ?? 'Assigned scope'}</span>
            <span>›</span>
            <span>{selected?.section.name ?? 'Select a section'}</span>
            <span>›</span>
            <span>{selected?.section.course.name}</span>
          </div>
          <h1 className="text-[26px] font-bold tracking-tight leading-7 text-white">Attendance</h1>
          <p className="mt-1 text-xs text-slate-300">Manage attendance for your assigned courses and sections.</p>
        </div>
        <div className="flex gap-2">
          <label className="relative hidden md:block">
            <span className="sr-only">Search students, register number</span>
            <span className="pointer-events-none absolute left-3 top-2 text-slate-500">
              <Glyph name="search" size={15} />
            </span>
            <input
              className={`${input} h-[30px] w-[243px] pl-9 text-[11px]`}
              placeholder="Search students, register number..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={exportAttendance}
            disabled={!selected || rosterIncomplete || sectionUnavailable}
            className="inline-flex items-center gap-2 rounded-md border border-[#69551d] bg-[#1f1b10] px-3 py-1.5 text-[11px] font-semibold text-[#ffc72c] hover:bg-[#30270f]"
          >
            <Glyph name="download" size={15} />
            Export <span aria-hidden="true">⌄</span>
          </button>
        </div>
      </div>

      {assignments.length === 0 ? (
        <EmptyAssignment />
      ) : (
        <>
          <div className={`${surface} grid gap-2.5 p-2 `}>
            <AttendanceAcademicFilters
              scopes={assignments}
              selectedId={selected?.assignment_id ?? ''}
              onChange={setAssignmentId}
            />
          </div>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            <AttendanceMetric label="Total Students" value={metrics.students} icon="users" tone="yellow" />
            <AttendanceMetric label="Classes Conducted" value={metrics.classes} icon="calendar" tone="cyan" />
            <AttendanceMetric
              label="Average Attendance"
              value={metrics.average === null ? null : `${metrics.average.toFixed(1)}%`}
              icon="clock"
              tone="green"
            />
            <AttendanceMetric label="Total Present" value={overview?.present ?? null} icon="users" tone="blue" />
            <AttendanceMetric label="Total Absent" value={overview?.absent ?? null} icon="users" tone="red" />
            <AttendanceMetric
              label={
                <>
                  Low Attendance <span className="block text-[10px] font-normal">(&lt; 75%)</span>
                </>
              }
              value={metrics.low}
              icon="alert"
              tone="amber"
            />
          </div>

          {overviewQuery.isPending && selected ? (
            <p role="status" className="text-xs text-slate-400">
              Loading attendance summary…
            </p>
          ) : refreshing ? (
            <p role="status" className="text-xs text-slate-400">
              Refreshing attendance…
            </p>
          ) : null}
          {loadError ? (
            <p
              role="alert"
              className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200"
            >
              {loadError instanceof Error ? loadError.message : 'Unable to load attendance'}
              <button type="button" onClick={() => void retry()} className="ml-3 underline">
                Try Again
              </button>
            </p>
          ) : null}

          {!canManage ? (
            <p className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-200">
              Monitoring access. Marking and imports require an active teaching assignment and attendance permission for
              this subject.
            </p>
          ) : null}
          <p className="text-xs text-slate-500">
            75% is a monitoring threshold. Percentages use present / all recorded statuses. Imported summaries do not
            create attendance history.
          </p>
          <AttendanceRoster model={model} />
        </>
      )}

      {message ? (
        <p
          role="status"
          className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300"
        >
          {message}
        </p>
      ) : null}
      {error && error !== 'Unable to load attendance' && error !== 'AI_CONFIRMATION_REQUIRED' ? (
        <p role="alert" className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      <MarkAttendanceDialog model={model} />
      <AttendanceUploadDialog model={model} />
      <AttendanceProfileDialog model={model} />
    </section>
  )
}

export default function FacultyAttendance(props: FacultyAttendanceProps) {
  return <FacultyAttendanceWorkspace key={JSON.stringify([props.accessToken, props.scopeVersion ?? ''])} {...props} />
}

import { getFacultyAttendanceImportReview } from '../../../../services/faculty/facultyAttendanceApi.ts'
import { AttendanceRecordedViews } from './AttendanceRecordedViews.tsx'
import { AttendanceRosterTable } from './AttendanceRosterTable.tsx'
import { Glyph, input, PAGE_SIZE, surface } from '../shared/AttendanceWorkspaceUi.tsx'
import type { FacultyAttendanceWorkspaceModel } from '../state/useAttendanceWorkspace.ts'
export function AttendanceRoster({ model }: { model: FacultyAttendanceWorkspaceModel }) {
  const {
    accessToken,
    sort,
    setSort,
    setReview,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    attendanceFilter,
    setAttendanceFilter,
    setPage,
    tab,
    setTab,
    setMarkOpen,
    setUploadOpen,
    setUploadStep,
    setUploadSuccess,
    saving,
    setSaving,
    setError,
    reloadKey,
    selected,
    roster,
    overview,
    studentsQuery,
    sectionUnavailable,
    rosterIncomplete,
    rosterLoading,
    canManage,
    filteredRoster,
    totalPages,
    currentPage,
    resetFilters,
  } = model
  return (
    <div className={`${surface} overflow-hidden`}>
      <div className="flex flex-col justify-between gap-2 border-b border-[#1e3348] px-2.5 pt-2 sm:flex-row sm:items-center sm:px-3">
        <div className="flex gap-1 overflow-x-auto">
          {(
            [
              ['students', 'Students', 'users'],
              ['history', 'Import History', 'clock'],
              ['sessions', 'Session-wise View', 'calendar'],
              ['reports', 'Reports', 'chart'],
            ] as const
          ).map(([key, label, icon]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`inline-flex shrink-0 items-center gap-2 border-b-2 px-2.5 py-2.5 text-[11px] font-semibold ${tab === key ? 'border-[#ffc72c] text-[#ffc72c]' : 'border-transparent text-slate-400 hover:text-white'}`}
            >
              <Glyph name={icon} size={14} />
              {label}
            </button>
          ))}
        </div>
        <div className="flex gap-2 pb-2 sm:pb-0">
          <button
            type="button"
            disabled={!canManage || saving || rosterIncomplete || sectionUnavailable}
            onClick={() => setMarkOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] hover:bg-[#ffd65d]"
          >
            <Glyph name="plus" size={14} />
            Mark Attendance
          </button>
          <button
            type="button"
            disabled={!canManage || saving}
            onClick={() => {
              setUploadOpen(true)
              setUploadStep(1)
              setUploadSuccess(false)
            }}
            className="inline-flex items-center gap-1.5 rounded-md bg-[#6538ed] px-3 py-1.5 text-[11px] font-bold text-white hover:bg-[#7d56ff]"
          >
            <Glyph name="upload" size={14} />
            Upload Attendance
          </button>
        </div>
      </div>

      {tab !== 'students' && selected ? (
        <AttendanceRecordedViews
          key={`${selected.section_id}:${reloadKey}`}
          token={accessToken}
          sectionId={selected.section_id}
          view={tab}
          overview={overview}
          onReview={(id) => {
            setSaving(true)
            getFacultyAttendanceImportReview(accessToken, id)
              .then((result) => {
                setReview(result)
                setUploadSuccess(false)
                setUploadOpen(true)
                setUploadStep(3)
              })
              .catch((cause: unknown) =>
                setError(cause instanceof Error ? cause.message : 'Unable to load import review'),
              )
              .finally(() => setSaving(false))
          }}
        />
      ) : (
        <>
          <div className="flex flex-col gap-2 border-b border-[#1e3348] p-2 sm:flex-row sm:items-center sm:px-2.5">
            <label className="relative min-w-0 flex-1">
              <span className="sr-only">Search by name, register number or university roll number</span>
              <span className="pointer-events-none absolute left-2.5 top-[7px] text-slate-500">
                <Glyph name="search" size={15} />
              </span>
              <input
                className={`${input} h-[29px] w-full pl-8 text-[11px]`}
                placeholder="Search by name, register number or university roll number..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <select
              aria-label="Filter by student status"
              className={`${input} h-[29px] w-full text-[11px] sm:w-[122px]`}
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="all">All Status</option>
              <option value="ACTIVE">Active</option>
              <option value="UNREGISTERED">Unregistered</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="INACTIVE">Inactive</option>
            </select>
            <select
              aria-label="Filter by attendance"
              className={`${input} h-[29px] w-full text-[11px] sm:w-[155px]`}
              value={attendanceFilter}
              onChange={(event) => setAttendanceFilter(event.target.value)}
            >
              <option value="all">All Attendance</option>
              <option value="good">75% and above</option>
              <option value="low">Below 75%</option>
              <option value="unknown">Not available</option>
            </select>
            <button
              type="button"
              onClick={resetFilters}
              className="h-[29px] rounded-md border border-[#263d55] px-4 text-[11px] font-semibold text-slate-300 hover:bg-[#142638]"
            >
              Reset
            </button>
          </div>
          <label className="block p-2 text-xs text-slate-400">
            Sort students
            <select
              aria-label="Sort students"
              value={sort}
              onChange={(event) => setSort(event.target.value)}
              className={input}
            >
              <option value="register_number">Register Number</option>
              <option value="student_name">Student Name</option>
              <option value="attendance">Attendance</option>
            </select>
          </label>
          {rosterIncomplete && !rosterLoading && !sectionUnavailable ? (
            <p role="status" className="px-3 pb-2 text-xs text-slate-400">
              Loading remaining students… {roster.length} of {studentsQuery.data?.pages[0]?.total ?? 0} loaded.
            </p>
          ) : null}
          {rosterLoading ? (
            <div role="status" className="space-y-2 p-4">
              {Array.from({ length: 5 }, (_, index) => (
                <div key={index} className="h-12 animate-pulse rounded bg-[#102235]" />
              ))}
            </div>
          ) : filteredRoster.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-400">No students match the current filters.</div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <AttendanceRosterTable model={model} />
              </div>
              <div className="flex flex-col justify-between gap-3 border-t border-[#1e3348] px-4 py-2.5 text-xs text-slate-400 sm:flex-row sm:items-center">
                <span>
                  Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredRoster.length)}{' '}
                  of {filteredRoster.length} students
                </span>
                <div className="flex items-center gap-1" aria-label="Attendance pagination">
                  <button
                    type="button"
                    aria-label="Previous page"
                    disabled={currentPage === 1}
                    onClick={() => setPage((value) => Math.max(1, value - 1))}
                    className="rounded p-1.5 text-slate-400 hover:bg-[#142638] hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    ‹
                  </button>
                  {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
                    <button
                      key={pageNumber}
                      type="button"
                      aria-label={`Page ${pageNumber}`}
                      aria-current={pageNumber === currentPage ? 'page' : undefined}
                      onClick={() => setPage(pageNumber)}
                      className={`min-w-7 rounded px-2 py-1.5 text-xs ${pageNumber === currentPage ? 'bg-[#1b2d43] font-semibold text-white' : 'text-slate-400 hover:bg-[#142638] hover:text-white'}`}
                    >
                      {pageNumber}
                    </button>
                  ))}
                  <button
                    type="button"
                    aria-label="Next page"
                    disabled={currentPage === totalPages}
                    onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                    className="rounded p-1.5 text-slate-400 hover:bg-[#142638] hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    ›
                  </button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}

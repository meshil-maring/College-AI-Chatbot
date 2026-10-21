import { ChevronLeft, ChevronRight } from 'lucide-react'
import { StudentsStats } from '../../../students/StudentsUI.tsx'
import ClassRegistrationDirectory from './ClassRegistrationDirectory.tsx'
import FacultyStudentRegistration from '../registration/FacultyStudentRegistration.tsx'
import {
  LoadError,
  PAGE_SIZE,
  ROSTER_STATUS_CARDS,
  STATUS_TONE,
  StudentDetails,
  type RosterStatus,
} from './rosterUi.tsx'
import { SectionRosterTable } from './SectionRosterTable.tsx'
import { SectionRosterToolbar } from './SectionRosterToolbar.tsx'
import { useSectionStudents } from './useSectionStudents.ts'

export function SectionStudents(props: Parameters<typeof useSectionStudents>[0]) {
  const model = useSectionStudents(props)
  const {
    token,
    assignment,
    assignments,
    batchId,
    onSectionChange,
    registrationOpen,
    waitingApproval,
    onBack,
    registrationMethod,
    onRegistrationMethod,
    filters,
    setFilters,
    setStudentId,
    registrationMessage,
    statusCounts,
    studentsQuery,
    result,
    totalPages,
    selectedStudent,
    updateFilters,
    registered,
  } = model

  if (registrationOpen) {
    return (
      <FacultyStudentRegistration
        token={token}
        assignment={assignment}
        assignments={assignments}
        onSectionChange={onSectionChange}
        onRegistered={registered}
        onCancel={onBack}
        method={registrationMethod}
        onMethodChange={onRegistrationMethod}
      />
    )
  }

  return (
    <>
      <ClassRegistrationDirectory
        key={`${assignment.section_id}:${batchId}:${filters.search}:${filters.registration}:${filters.sort}`}
        token={token}
        sectionId={assignment.section_id}
        waitingApproval={waitingApproval}
        registration={(filters.registration as RosterStatus) || undefined}
        filters={{
          batchId,
          search: filters.search,
          sort: filters.sort === 'student_name' ? 'student_name' : 'register_number',
        }}
      />
      <section className="students-directory" aria-label="Student directory">
        {waitingApproval ? null : (
          <StudentsStats
            items={ROSTER_STATUS_CARDS.map(({ status, title, description, Icon }) => {
              const count = statusCounts[status]
              const selected = filters.registration === status
              return {
                key: status,
                title,
                description,
                Icon,
                tone: STATUS_TONE[status],
                selected,
                value: count.isError ? '—' : count.isPending ? '…' : (count.data?.total ?? 0),
                onSelect: () => updateFilters({ registration: selected ? '' : status }),
              }
            })}
          />
        )}
        <SectionRosterToolbar model={model} />
        {registrationMessage ? (
          <p
            role="status"
            className="rounded-lg border border-emerald-800 bg-emerald-900/20 p-3 text-sm text-emerald-200"
          >
            {registrationMessage}
          </p>
        ) : null}
        {studentsQuery.isError ? (
          <LoadError
            error={studentsQuery.error}
            onRetry={() => {
              void studentsQuery.refetch()
            }}
          />
        ) : studentsQuery.isPending ? (
          <p role="status" className="py-10 text-center text-sm text-slate-400">
            Loading students…
          </p>
        ) : result?.items.length ? (
          <>
            <div className="students-table-scroll">
              <SectionRosterTable model={model} />
            </div>
          </>
        ) : (
          <div role="status" className="students-empty">
            <h3 className="font-medium text-white">
              {filters.search || filters.registration || batchId
                ? 'No students match your filters'
                : waitingApproval
                  ? 'No students waiting for approval'
                  : 'No students in this section yet'}
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              {filters.search || filters.registration || batchId
                ? 'Try another search, batch, or clear the filters. Batch matches saved admission cohorts.'
                : waitingApproval
                  ? 'There are no pending student accounts in this section.'
                  : 'Students appear here after they are added to the section roster.'}
            </p>
          </div>
        )}
        {result ? (
          <div className="students-pagination">
            <p role="status">
              {result.total === 0
                ? '0 students'
                : !result.items.length
                  ? `0 of ${result.total} students on this page`
                  : `${filters.page * PAGE_SIZE + 1}–${filters.page * PAGE_SIZE + result.items.length} of ${result.total} students`}
            </p>
            <div>
              <button
                type="button"
                className="students-page"
                aria-label="Previous page"
                disabled={filters.page === 0 || studentsQuery.isFetching}
                onClick={() => {
                  setStudentId(null)
                  setFilters((current) => ({ ...current, page: current.page - 1 }))
                }}
              >
                <ChevronLeft aria-hidden="true" />
              </button>
              {Array.from(
                { length: 5 },
                (_, index) => Math.min(Math.max(1, filters.page - 1), Math.max(1, totalPages - 4)) + index,
              )
                .filter((number) => number <= totalPages)
                .map((number) => (
                  <button
                    key={number}
                    type="button"
                    className={`students-page ${filters.page + 1 === number ? 'active' : ''}`}
                    aria-label={`Page ${number}`}
                    aria-current={filters.page + 1 === number ? 'page' : undefined}
                    onClick={() => {
                      setStudentId(null)
                      setFilters((current) => ({ ...current, page: number - 1 }))
                    }}
                  >
                    {number}
                  </button>
                ))}
              <button
                type="button"
                className="students-page"
                aria-label="Next page"
                disabled={(filters.page + 1) * PAGE_SIZE >= result.total || studentsQuery.isFetching}
                onClick={() => {
                  setStudentId(null)
                  setFilters((current) => ({ ...current, page: current.page + 1 }))
                }}
              >
                <ChevronRight aria-hidden="true" />
              </button>
            </div>
          </div>
        ) : null}
      </section>
      {selectedStudent ? (
        <StudentDetails
          key={selectedStudent.roster_id}
          token={token}
          rosterId={selectedStudent.roster_id}
          onClose={() => setStudentId(null)}
        />
      ) : null}
    </>
  )
}

import { RefreshCw, UserPlus } from 'lucide-react'
import { StudentsSearch } from '../../../students/StudentsUI.tsx'
import { STATUS_LABELS } from './rosterUi.tsx'
import type { SectionStudentsModel } from './useSectionStudents.ts'

export function SectionRosterToolbar({ model }: { model: SectionStudentsModel }) {
  const {
    assignment,
    batchId,
    onClearBatch,
    waitingApproval,
    onRegister,
    filters,
    draftSearch,
    setDraftSearch,
    setStudentId,
    setRegistrationMessage,
    studentsQuery,
    updateFilters,
  } = model
  return (
    <div className="students-toolbar">
      <div className="students-toolbar-heading">
        <h2>{waitingApproval ? 'Waiting approval' : `${assignment.section.name} roster`}</h2>
        <p>
          {waitingApproval
            ? 'Students awaiting account approval in this section. An administrator or authorized staff member reviews approvals.'
            : `${assignment.section.course.name} · Attendance shown for this subject only.`}
        </p>
      </div>
      <div className="students-table-actions">
        <StudentsSearch
          value={draftSearch}
          onChange={setDraftSearch}
          onSubmit={() => updateFilters({ search: draftSearch.trim() })}
        />
        {!waitingApproval ? (
          <label className="students-filter-label">
            Registration status
            <select
              value={filters.registration}
              onChange={(event) => updateFilters({ registration: event.target.value })}
            >
              <option value="">All statuses</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="students-filter-label">
          Sort by
          <select value={filters.sort} onChange={(event) => updateFilters({ sort: event.target.value })}>
            <option value="register_number">Register number</option>
            <option value="student_name">Student name</option>
            <option value="attendance_percentage">Attendance</option>
          </select>
        </label>
        {filters.search || filters.registration || batchId ? (
          <button
            type="button"
            className="students-button"
            onClick={() => {
              setDraftSearch('')
              updateFilters({ search: '', registration: '' })
              onClearBatch()
            }}
          >
            Clear filters
          </button>
        ) : null}
        <button
          type="button"
          className="students-button"
          disabled={studentsQuery.isFetching}
          onClick={() => {
            setStudentId(null)
            void studentsQuery.refetch()
          }}
        >
          <RefreshCw aria-hidden="true" />
          Refresh students
        </button>
        {assignment.can_manage ? (
          <button
            type="button"
            className="students-button primary"
            disabled={studentsQuery.isError}
            onClick={() => {
              setRegistrationMessage('')
              setStudentId(null)
              onRegister()
            }}
          >
            <UserPlus aria-hidden="true" />
            Register new student
          </button>
        ) : null}
      </div>
    </div>
  )
}

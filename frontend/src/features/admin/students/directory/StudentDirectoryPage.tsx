import { useState, type FormEvent } from 'react'
import { RefreshCw, Search, UsersRound } from 'lucide-react'
import type { StudentDirectoryFilter } from '../../../../types/admin/students.ts'
import StudentDirectoryTable from './StudentDirectoryTable.tsx'
import { STUDENT_DIRECTORY_PAGE_SIZE } from './studentDirectoryQueries.ts'
import { useStudentDirectory } from './useStudentDirectory.ts'
import './studentDirectory.css'
import { useStudentManagementActions } from './useStudentManagementActions.ts'

const filters: { value: StudentDirectoryFilter; label: string }[] = [
  { value: 'all', label: 'All students' },
  { value: 'pending_sign_in', label: 'Awaiting sign-in' },
  { value: 'signed_in', label: 'Signed in' },
  { value: 'no_signin', label: 'No sign-in yet' },
]

export default function StudentDirectoryPage({
  accessToken,
  identity,
  canUpdateStudents = false,
  canManageStudentPlacement = false,
  canDeleteStudents = false,
  canResendInvitations = false,
}: {
  accessToken: string
  identity: string
  canUpdateStudents?: boolean
  canManageStudentPlacement?: boolean
  canDeleteStudents?: boolean
  canResendInvitations?: boolean
}) {
  const directory = useStudentDirectory(accessToken, identity)
  const actions = useStudentManagementActions(accessToken, identity, canManageStudentPlacement)
  const [refreshing, setRefreshing] = useState(false)
  const data = directory.query.data
  const summary = data?.summary
  const structure = actions.structure.data
  const placementError =
    actions.structure.error instanceof Error
      ? actions.structure.error.message
      : actions.structure.isError
        ? 'Academic sections are unavailable.'
        : ''
  const errorMessage =
    directory.query.error instanceof Error
      ? directory.query.error.message
      : 'The student directory could not be loaded.'

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    directory.submitSearch()
  }

  async function refresh() {
    setRefreshing(true)
    try {
      await directory.query.refetch()
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <section className="student-directory" aria-labelledby="student-directory-heading">
      <header className="student-directory-header">
        <div>
          <p className="student-directory-eyebrow">Student management</p>
          <h1 id="student-directory-heading">All Students</h1>
          <p>Review student accounts, setup invitations, and academic placement.</p>
        </div>
        <button type="button" className="student-directory-refresh" onClick={refresh} disabled={refreshing}>
          <RefreshCw aria-hidden="true" className={refreshing ? 'is-spinning' : ''} />
          Refresh
        </button>
      </header>

      <div className="student-directory-summary" aria-label="Student account summary">
        <SummaryCard label="Total records" value={summary?.total} />
        <SummaryCard label="Awaiting sign-in" value={summary?.pending_sign_in} />
        <SummaryCard label="Signed in" value={summary?.signed_in} />
        <SummaryCard label="No sign-in yet" value={summary?.no_signin} />
      </div>

      <div className="student-directory-content">
        <div className="student-directory-toolbar">
          <div className="student-directory-tabs" role="group" aria-label="Filter by account status">
            {filters.map((filter) => (
              <button
                type="button"
                key={filter.value}
                aria-pressed={directory.status === filter.value}
                onClick={() => directory.setStatus(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <form className="student-directory-filters" role="search" onSubmit={search}>
            <label className="student-directory-search">
              <Search aria-hidden="true" />
              <span className="sr-only">Search students</span>
              <input
                type="search"
                value={directory.searchInput}
                onChange={(event) => directory.setSearchInput(event.target.value)}
                placeholder="Search name, register no., roll no., or email"
              />
            </label>
            <label className="student-directory-program">
              <span className="sr-only">Filter by program</span>
              <select
                aria-label="Filter by program"
                value={directory.programId}
                onChange={(event) => directory.setProgramId(event.target.value)}
              >
                <option value="">All programs</option>
                {(data?.programs ?? []).map((program) => (
                  <option key={program.program_id} value={program.program_id}>
                    {program.program_name} ({program.program_code})
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="student-directory-search-button">
              Search
            </button>
            {directory.hasFilters && (
              <button type="button" className="student-directory-clear" onClick={directory.clearFilters}>
                Clear filters
              </button>
            )}
          </form>
        </div>

        <div className="student-directory-results">
          {actions.message && (
            <p className="student-directory-action-message" role="status">
              {actions.message}
            </p>
          )}
          {actions.error && (
            <p className="student-directory-action-message is-error" role="alert">
              {actions.error}
            </p>
          )}
          <div className="student-directory-results-heading">
            <div>
              <h2>Student records</h2>
              <p>Includes registered accounts and pending sign-in invitations.</p>
            </div>
            {data && (
              <span>
                {data.total} {data.total === 1 ? 'record' : 'records'}
              </span>
            )}
          </div>
          {directory.query.isPending && (
            <p className="student-directory-state" role="status">
              Loading student directory…
            </p>
          )}
          {directory.query.isError && (
            <div className="student-directory-state is-error" role="alert">
              <p>{errorMessage}</p>
              <button type="button" onClick={refresh}>
                Retry
              </button>
            </div>
          )}
          {data && !directory.query.isError && data.summary.total > 0 && (
            <StudentDirectoryTable
              rows={data.items}
              total={data.total}
              offset={(directory.page - 1) * STUDENT_DIRECTORY_PAGE_SIZE}
              page={directory.page}
              pages={directory.pages}
              setPage={directory.setPage}
              permissions={{
                canEdit: canUpdateStudents,
                canManagePlacement: canManageStudentPlacement,
                canDelete: canDeleteStudents,
                canResend: canResendInvitations,
              }}
              sections={structure?.records.academic_sections ?? []}
              cohorts={structure?.records.admission_cohorts ?? []}
              busyId={actions.busyId}
              structureLoading={actions.structure.isPending}
              structureError={placementError}
              onEdit={actions.edit}
              onSetActive={actions.setActive}
              onDelete={actions.remove}
              onCancelInvitation={actions.cancelInvitation}
              onResend={(row) => void actions.resend(row)}
            />
          )}
          {!directory.query.isPending && !directory.query.isError && data?.summary.total === 0 && (
            <div className="student-directory-first-empty">
              <UsersRound aria-hidden="true" />
              <p>No student accounts or setup invitations have been added yet.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function SummaryCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <article className="student-directory-metric">
      <span>{label}</span>
      <strong>{value === undefined ? '—' : value.toLocaleString()}</strong>
    </article>
  )
}

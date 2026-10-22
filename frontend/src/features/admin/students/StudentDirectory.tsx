import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  GraduationCap,
  RefreshCw,
  UserPlus,
  Users,
} from 'lucide-react'
import { StudentsPageHeader, StudentsSearch, StudentsStats } from '../../students/StudentsUI.tsx'
import { useStudentDirectory } from './directory/useStudentDirectory.ts'

export default function StudentDirectory(props: Parameters<typeof useStudentDirectory>[0]) {
  const model = useStudentDirectory(props)
  const {
    students,
    loading,
    refreshing,
    error,
    onSearch,
    onRefresh,
    onSection,
    status,
    setStatus,
    setPage,
    filters,
    setFilters,
    draftSearch,
    setDraftSearch,
    filtered,
    pages,
    currentPage,
    visible,
    stats,
    exportRows,
  } = model

  return (
    <section className="students-content students-scope" aria-label="Student directory">
      <StudentsPageHeader
        page="All Student"
        title="Students"
        description="Your students, their records, and a clearer view of your institution."
        actions={
          <>
            <button type="button" className="students-button primary" onClick={() => onSection('register')}>
              <UserPlus aria-hidden="true" />
              Register new student
            </button>
          </>
        }
      />
      <StudentsStats
        items={stats.map(({ title, value, Icon, color, filter, description }) => ({
          key: filter,
          title,
          description,
          value: loading || error ? '—' : value,
          Icon,
          tone: color,
          selected: status === filter,
          onSelect: () => {
            setStatus(status === filter ? 'all' : filter)
            setPage(1)
          },
        }))}
      />
      <div className="students-toolbar">
        <div className="students-toolbar-heading">
          <h2>All Student{!loading && !error ? ` (${students.length})` : ''}</h2>
          <p>Institution student records</p>
        </div>
        <div className="students-table-actions">
          <StudentsSearch
            label="Search students by number"
            placeholder="Search student number…"
            value={draftSearch}
            onChange={setDraftSearch}
            onSubmit={() => {
              onSearch(draftSearch.trim())
              setPage(1)
            }}
          />
          <button
            className="students-button"
            aria-expanded={filters}
            aria-controls="student-directory-filters"
            onClick={() => setFilters(!filters)}
          >
            <Filter />
            Filters{status !== 'all' ? ' (1)' : ''}
          </button>
          <button className="students-button" aria-label="Refresh students" disabled={refreshing} onClick={onRefresh}>
            <RefreshCw aria-hidden="true" className={refreshing ? 'animate-spin' : ''} />
            Refresh students
          </button>
        </div>
      </div>
      {filters && (
        <div className="students-filter-panel" id="student-directory-filters">
          <label>
            Status{' '}
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="graduated">Graduated</option>
              <option value="withdrawn">Withdrawn</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <button
            className="students-text-button"
            onClick={() => {
              setStatus('all')
              onSearch('')
              setPage(1)
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      {error ? (
        <div className="students-alert error" role="alert">
          <span>{error}</span>
          <button className="students-button" disabled={refreshing} onClick={onRefresh}>
            Retry
          </button>
        </div>
      ) : loading ? (
        <div className="students-empty" role="status">
          Loading students…
        </div>
      ) : (
        <div className="students-table-scroll">
          <table className="students-table directory">
            <caption className="sr-only">Institution student records</caption>
            <thead>
              <tr>
                <th>#</th>
                <th>Student Number</th>
                <th>Status</th>
                <th>Enrollment Date</th>
                <th>Expected Graduation</th>
                <th>Record</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((student, index) => (
                <tr key={student.student_id}>
                  <td>{(currentPage - 1) * 10 + index + 1}</td>
                  <td>
                    <span className="students-roster-identity">
                      <span>
                        <GraduationCap />
                      </span>
                      <strong>{student.student_number}</strong>
                    </span>
                  </td>
                  <td>
                    <span
                      className={`students-status ${student.status === 'active' && student.is_active ? 'valid' : student.status === 'graduated' ? 'duplicate' : 'neutral'}`}
                    >
                      <span className="students-status-dot" />
                      {student.status}
                    </span>
                  </td>
                  <td>{student.enrollment_date ?? '—'}</td>
                  <td>{student.expected_graduation_date ?? '—'}</td>
                  <td>{student.is_active ? 'Current' : 'Archived'}</td>
                </tr>
              ))}
              {!visible.length && (
                <tr>
                  <td colSpan={6} className="students-empty">
                    <Users />
                    <h2>{students.length ? 'No matching students' : 'Your student directory starts here'}</h2>
                    <p>
                      {students.length
                        ? 'Try another student number or clear your filters.'
                        : 'No students found for your institution. Review registration requests or prepare a bulk import.'}
                    </p>
                    <button
                      className="students-text-button"
                      onClick={() => {
                        if (students.length) {
                          setStatus('all')
                          onSearch('')
                          setPage(1)
                        } else onSection('waiting-approval')
                      }}
                    >
                      {students.length ? 'Clear filters' : 'Review waiting approvals'}
                      <ArrowRight />
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <div className="students-pagination">
        <p>
          {!loading && !error
            ? `Showing ${filtered.length ? (currentPage - 1) * 10 + 1 : 0}–${Math.min(currentPage * 10, filtered.length)} of ${filtered.length} students`
            : 'Institution student records'}
        </p>
        <div>
          <button
            className="students-button"
            disabled={loading || Boolean(error) || !filtered.length}
            onClick={exportRows}
          >
            <Download />
            Export CSV
          </button>
          <button
            className="students-page"
            aria-label="Previous student page"
            disabled={currentPage === 1}
            onClick={() => setPage(currentPage - 1)}
          >
            <ChevronLeft />
          </button>
          <span className="students-page active">{currentPage}</span>
          <button
            className="students-page"
            aria-label="Next student page"
            disabled={currentPage === pages}
            onClick={() => setPage(currentPage + 1)}
          >
            <ChevronRight />
          </button>
        </div>
      </div>
    </section>
  )
}

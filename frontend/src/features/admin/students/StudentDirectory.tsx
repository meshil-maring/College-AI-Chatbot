import { useState } from 'react'
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  GraduationCap,
  RefreshCw,
  Search,
  Upload,
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import type { Student } from '../../../types/admin.ts'
import { downloadCsv } from './studentImport.ts'
import type { StudentSection } from './studentSections.ts'

export default function StudentDirectory({
  students,
  loading,
  refreshing,
  error,
  search,
  onSearch,
  onRefresh,
  onSection,
}: {
  students: Student[]
  loading: boolean
  refreshing: boolean
  error: string | null
  search: string
  onSearch: (search: string) => void
  onRefresh: () => void
  onSection: (section: StudentSection) => void
}) {
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState(false)
  const filtered = students.filter(
    (student) =>
      (status === 'all' ||
        (status === 'archived'
          ? !student.is_active
          : student.is_active && student.status === status)) &&
      student.student_number
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
  )
  const pages = Math.max(1, Math.ceil(filtered.length / 10))
  const currentPage = Math.min(page, pages)
  const visible = filtered.slice((currentPage - 1) * 10, currentPage * 10)
  const stats = [
    {
      title: 'Total Students',
      value: students.length,
      Icon: Users,
      color: 'neutral',
      filter: 'all',
      description: 'Across your institution',
    },
    {
      title: 'Active Students',
      value: students.filter(
        (student) => student.is_active && student.status === 'active',
      ).length,
      Icon: UserCheck,
      color: 'valid',
      filter: 'active',
      description: 'Currently enrolled',
    },
    {
      title: 'Graduated',
      value: students.filter(
        (student) => student.is_active && student.status === 'graduated',
      ).length,
      Icon: GraduationCap,
      color: 'duplicate',
      filter: 'graduated',
      description: 'Completed their studies',
    },
    {
      title: 'Archived Students',
      value: students.filter((student) => !student.is_active).length,
      Icon: Users,
      color: 'invalid',
      filter: 'archived',
      description: 'Academic records retained',
    },
  ]
  const exportRows = () =>
    downloadCsv('students.csv', [
      [
        'student_number',
        'status',
        'enrollment_date',
        'expected_graduation_date',
        'is_active',
      ],
      ...filtered.map((student) => [
        student.student_number,
        student.status,
        student.enrollment_date,
        student.expected_graduation_date,
        student.is_active,
      ]),
    ])
  return (
    <section className="students-content" aria-label="Student directory">
      <div className="students-breadcrumb">
        <span>Students</span>
        <ChevronRight />
        <span aria-current="page">All Students</span>
      </div>
      <div className="students-title">
        <div>
          <h1>Students</h1>
          <p>
            Your students, their records, and a clearer view of your
            institution.
          </p>
        </div>
        <div className="students-heading-actions">
          <button
            className="students-button"
            onClick={() => onSection('import')}
          >
            <Upload />
            Bulk Import
          </button>
          <button
            className="students-button primary"
            onClick={() => onSection('add')}
          >
            <UserPlus />
            Add Student
          </button>
        </div>
      </div>
      <div className="students-stats">
        {stats.map(({ title, value, Icon, color, filter, description }) => (
          <button
            key={title}
            className={`students-stat ${color} ${status === filter ? 'is-selected' : ''}`}
            aria-pressed={status === filter}
            onClick={() => {
              setStatus(filter)
              setPage(1)
            }}
          >
            <span className="students-stat-icon">
              <Icon />
            </span>
            <span>
              <strong>{loading || error ? '—' : value.toLocaleString()}</strong>
              <b>{title}</b>
              <small>{description}</small>
            </span>
          </button>
        ))}
      </div>
      <div className="students-toolbar">
        <div className="students-tabs">
          <button
            className="active"
            onClick={() => {
              setStatus('all')
              setPage(1)
            }}
          >
            All Students{!loading && !error ? ` (${students.length})` : ''}
          </button>
        </div>
        <div className="students-table-actions">
          <label className="students-search">
            <Search />
            <input
              type="search"
              aria-label="Search students by number"
              placeholder="Search student number…"
              value={search}
              onChange={(event) => {
                onSearch(event.target.value)
                setPage(1)
              }}
            />
          </label>
          <button
            className="students-button"
            aria-expanded={filters}
            aria-controls="student-directory-filters"
            onClick={() => setFilters(!filters)}
          >
            <Filter />
            Filters{status !== 'all' ? ' (1)' : ''}
          </button>
          <button
            className="students-button icon-only"
            aria-label="Refresh students"
            disabled={refreshing}
            onClick={onRefresh}
          >
            <RefreshCw className={refreshing ? 'animate-spin' : ''} />
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
          <button
            className="students-button"
            disabled={refreshing}
            onClick={onRefresh}
          >
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
                    <h2>
                      {students.length
                        ? 'No matching students'
                        : 'Your student directory starts here'}
                    </h2>
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
                        } else onSection('requests')
                      }}
                    >
                      {students.length
                        ? 'Clear filters'
                        : 'Review Registration Requests'}
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

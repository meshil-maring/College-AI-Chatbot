import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { useState } from 'react'
import type { StudentImportRow } from './studentImport.ts'

type EditableField = 'student_name' | 'register_number' | 'university_roll_number' | 'email'
type ReviewFilter = 'all' | 'valid' | 'duplicate' | 'invalid'
const pageSize = 8

function rowStatus(row: StudentImportRow): Exclude<ReviewFilter, 'all'> {
  if (!row.errors.length) return 'valid'
  return row.errors.some((error) => error.toLowerCase().includes('duplicates')) ? 'duplicate' : 'invalid'
}

export default function StudentImportReview({
  rows,
  disabled,
  onEdit,
  onRemove,
}: {
  rows: StudentImportRow[]
  disabled: boolean
  onEdit: (sourceRow: number, field: EditableField, value: string) => void
  onRemove: (sourceRow: number) => void
}) {
  const [filter, setFilter] = useState<ReviewFilter>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  if (!rows.length) return null
  const counts = rows.reduce(
    (result, row) => {
      result[rowStatus(row)] += 1
      return result
    },
    { valid: 0, duplicate: 0, invalid: 0 },
  )
  const normalizedSearch = search.trim().toLowerCase()
  const filteredRows = rows.filter((row) => {
    const matchesStatus = filter === 'all' || rowStatus(row) === filter
    const matchesSearch =
      !normalizedSearch ||
      [row.student_name, row.register_number, row.university_roll_number ?? '', row.email]
        .join(' ')
        .toLowerCase()
        .includes(normalizedSearch)
    return matchesStatus && matchesSearch
  })
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize))
  const currentPage = Math.min(page, pageCount)
  const visibleRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  return (
    <div className="student-import-review" aria-label="Imported student review">
      <div className="student-import-review-toolbar">
        <div className="student-import-review-filters" role="group" aria-label="Filter imported records">
          {(
            [
              ['all', 'All Records', rows.length],
              ['valid', 'Valid', counts.valid],
              ['duplicate', 'Duplicate', counts.duplicate],
              ['invalid', 'Invalid', counts.invalid],
            ] as const
          ).map(([value, label, count]) => (
            <button
              type="button"
              key={value}
              aria-pressed={filter === value}
              onClick={() => {
                setFilter(value)
                setPage(1)
              }}
            >
              {label} <span>{count}</span>
            </button>
          ))}
        </div>
        <label className="student-import-review-search">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search imported students</span>
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            placeholder="Search name, register no., roll no., or email"
          />
        </label>
      </div>
      <div className="student-import-table-wrap" role="region" aria-label="Imported student rows" tabIndex={0}>
        <table className="student-import-table">
          <caption className="sr-only">
            Edit student details, fix highlighted rows, or remove students before sending invitations.
          </caption>
          <thead>
            <tr>
              <th>File row</th>
              <th>Student Name*</th>
              <th>Register Number*</th>
              <th>University Roll No.</th>
              <th>Email*</th>
              <th>Review</th>
              <th>
                <span className="sr-only">Remove row</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => (
              <tr key={row.sourceRow} className={`is-${rowStatus(row)}`}>
                <th scope="row">{row.sourceRow}</th>
                <td>
                  <input
                    aria-label={`Student Name row ${row.sourceRow}`}
                    aria-invalid={row.errors.some((item) => item.includes('Student Name'))}
                    value={row.student_name}
                    disabled={disabled}
                    onChange={(event) => onEdit(row.sourceRow, 'student_name', event.target.value)}
                  />
                </td>
                <td>
                  <input
                    aria-label={`Register Number row ${row.sourceRow}`}
                    aria-invalid={row.errors.some((item) => item.includes('Register Number'))}
                    value={row.register_number}
                    disabled={disabled}
                    onChange={(event) => onEdit(row.sourceRow, 'register_number', event.target.value)}
                  />
                </td>
                <td>
                  <input
                    aria-label={`University Roll No row ${row.sourceRow}`}
                    aria-invalid={row.errors.some((item) => item.includes('University Roll'))}
                    value={row.university_roll_number ?? ''}
                    disabled={disabled}
                    onChange={(event) => onEdit(row.sourceRow, 'university_roll_number', event.target.value)}
                  />
                </td>
                <td>
                  <input
                    aria-label={`Email row ${row.sourceRow}`}
                    type="email"
                    aria-invalid={row.errors.some((item) => item.includes('Email'))}
                    value={row.email}
                    disabled={disabled}
                    onChange={(event) => onEdit(row.sourceRow, 'email', event.target.value)}
                  />
                </td>
                <td>
                  <span className={`student-import-status is-${rowStatus(row)}`}>
                    {rowStatus(row) === 'valid' ? 'Valid' : rowStatus(row) === 'duplicate' ? 'Duplicate' : 'Invalid'}
                  </span>
                  {row.errors.length ? (
                    <ul>
                      {row.errors.map((error) => (
                        <li key={error}>{error}</li>
                      ))}
                    </ul>
                  ) : (
                    'Ready'
                  )}
                </td>
                <td>
                  <button
                    type="button"
                    className="student-onboarding-text-button"
                    disabled={disabled}
                    onClick={() => onRemove(row.sourceRow)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {!visibleRows.length && (
              <tr>
                <td colSpan={7} className="student-import-empty">
                  No imported records match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <footer className="student-import-review-pagination">
        <span aria-live="polite">
          {filteredRows.length
            ? `Showing ${(currentPage - 1) * pageSize + 1}–${Math.min(currentPage * pageSize, filteredRows.length)} of ${filteredRows.length} records`
            : 'No records to show'}
        </span>
        <div>
          <button
            type="button"
            aria-label="Previous page"
            disabled={currentPage === 1}
            onClick={() => setPage(currentPage - 1)}
          >
            <ChevronLeft size={17} />
          </button>
          <span>
            Page {currentPage} of {pageCount}
          </span>
          <button
            type="button"
            aria-label="Next page"
            disabled={currentPage === pageCount}
            onClick={() => setPage(currentPage + 1)}
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </footer>
    </div>
  )
}

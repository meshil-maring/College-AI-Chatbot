import type { StudentImportModel } from './useStudentImport.ts'
import { statuses } from './useStudentImport.ts'

export function ImportPreviewTable({ model }: { model: StudentImportModel }) {
  const {
    registration,
    busy,
    setFilter,
    setSearch,
    setPage,
    selected,
    setSelected,
    setOnlySelected,
    visible,
    selectable,
    allSelected,
    toggle,
  } = model
  return (
    <div className="students-table-scroll">
      <table className="students-table">
        <caption className="sr-only">Student file validation preview</caption>
        <thead>
          <tr>
            <th className="selection">
              <input
                type="checkbox"
                aria-label="Select all valid records on this page"
                disabled={!selectable.length || busy}
                checked={allSelected}
                ref={(element) => {
                  if (element) element.indeterminate = !allSelected && selectable.some((row) => selected.has(row.row))
                }}
                onChange={() =>
                  setSelected((previous) => {
                    const next = new Set(previous)
                    selectable.forEach((row) => {
                      if (allSelected) next.delete(row.row)
                      else next.add(row.row)
                    })
                    return next
                  })
                }
              />
            </th>
            <th>#</th>
            <th>Name</th>
            <th>Register Number</th>
            <th>University Roll No</th>
            <th>Email</th>
            {!registration && <th>Attendance %</th>}
            <th>Status</th>
            <th>Validation Message</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => {
            const { Icon, label } = statuses[row.status]
            return (
              <tr key={row.row} className={row.status}>
                <td className="selection">
                  <input
                    type="checkbox"
                    aria-label={`Select ${row.name || `row ${row.row}`}`}
                    checked={row.status === 'valid' && selected.has(row.row)}
                    disabled={row.status !== 'valid' || busy}
                    onChange={() => toggle(row.row)}
                  />
                </td>
                <td>{row.row - 1}</td>
                <td className="student-name">{row.name || '—'}</td>
                <td>{row.registerNumber || '—'}</td>
                <td>{row.rollNumber || '—'}</td>
                <td>{row.email || '—'}</td>
                {!registration && <td>{row.attendance ? `${row.attendance}%` : '—'}</td>}
                <td>
                  <span className={`students-status ${row.status}`}>
                    <Icon />
                    {label}
                  </span>
                </td>
                <td className="validation-message">{row.message}</td>
              </tr>
            )
          })}
          {!visible.length && (
            <tr>
              <td colSpan={registration ? 8 : 9} className="students-empty">
                No records match these filters.
                <button
                  className="students-text-button"
                  onClick={() => {
                    setSearch('')
                    setFilter('all')
                    setOnlySelected(false)
                    setPage(1)
                  }}
                >
                  Clear filters
                </button>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Eye, Pencil, Trash2 } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { useDepartments } from './useDepartments.ts'
import { DEPARTMENT_PAGE_SIZE, departmentPrograms } from './departmentModel.ts'
import DepartmentListState from './DepartmentListState.tsx'

export function DepartmentBadge({ active }: { active: boolean }) {
  return (
    <span className={`department-badge ${active ? 'is-active' : 'is-inactive'}`}>
      <span aria-hidden="true" />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

interface Props {
  state: ReturnType<typeof useDepartments>
  onCreate: () => void
  onOpen: (mode: 'view' | 'edit', record: Department) => void
  onDelete: (record: Department) => void
  saving: boolean
}
export default function DepartmentTable({ state, onCreate, onOpen, onDelete, saving }: Props) {
  const { loading, rows, filtered, page, pages } = state
  function sortable(field: 'name' | 'code', label: string) {
    const selected = state.sort.startsWith(field)
    const descending = state.sort.endsWith('desc')
    const Icon = selected ? (descending ? ArrowDown : ArrowUp) : ArrowUpDown
    return (
      <th scope="col" aria-sort={selected ? (descending ? 'descending' : 'ascending') : 'none'}>
        <button
          type="button"
          disabled={!state.records}
          onClick={() => state.setSort(`${field}-${selected && !descending ? 'desc' : 'asc'}`)}
        >
          {label}
          <Icon aria-hidden="true" />
        </button>
      </th>
    )
  }
  return (
    <section className="department-table-panel" aria-label="Department records" aria-busy={loading}>
      {loading && (
        <p className="sr-only" role="status">
          Loading departments…
        </p>
      )}
      <table className="department-table">
        <caption className="sr-only">Departments in your institution</caption>
        <thead>
          <tr>
            {sortable('name', 'Department')}
            {sortable('code', 'Code')}
            <th scope="col">Programs</th>
            <th scope="col">Status</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: DEPARTMENT_PAGE_SIZE }, (_, i) => (
              <tr key={i} className="department-loading-row" aria-hidden="true">
                {Array.from({ length: 5 }, (_, j) => (
                  <td key={j}>
                    <span className="department-skeleton" />
                  </td>
                ))}
              </tr>
            ))
          ) : !rows.length ? (
            <tr>
              <td colSpan={5}>
                <DepartmentListState state={state} onCreate={onCreate} />
              </td>
            </tr>
          ) : (
            rows.map((record, index) => {
              const programs = departmentPrograms(state.catalogue, record.department_id)
              return (
                <tr key={record.department_id}>
                  <td data-label="Department">
                    <div className="department-identity">
                      <span className={`department-avatar tone-${index % 5}`} aria-hidden="true">
                        {record.name.slice(0, 1).toLocaleUpperCase()}
                      </span>
                      <div>
                        <strong>{record.name}</strong>
                        {record.description && <p>{record.description}</p>}
                      </div>
                    </div>
                  </td>
                  <td data-label="Code">
                    <span className="department-code">{record.code}</span>
                  </td>
                  <td data-label="Programs">
                    {programs === undefined ? (
                      <span className="department-unavailable">
                        —<small>Unavailable</small>
                      </span>
                    ) : (
                      programs.length
                    )}
                  </td>
                  <td data-label="Status">
                    <DepartmentBadge active={record.is_active} />
                  </td>
                  <td data-label="Actions">
                    <div className="department-row-actions">
                      <button
                        type="button"
                        onClick={() => onOpen('view', record)}
                        aria-label={`View ${record.name}`}
                        title="View details"
                      >
                        <Eye aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onOpen('edit', record)}
                        aria-label={`Edit ${record.name}`}
                        title={state.manageable ? 'Edit department' : 'Read-only access'}
                        disabled={!state.manageable || state.busy || saving}
                      >
                        <Pencil aria-hidden="true" />
                      </button>
                      {state.manageable && (
                        <button
                          type="button"
                          onClick={() => onDelete(record)}
                          aria-label={`Delete ${record.name}`}
                          title="Delete unused department"
                          disabled={state.busy || saving}
                        >
                          <Trash2 aria-hidden="true" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
      <footer className="department-pagination">
        <p role="status">
          {loading
            ? 'Loading departments…'
            : !state.records
              ? 'Count unavailable'
              : filtered.length
                ? `Showing ${(page - 1) * DEPARTMENT_PAGE_SIZE + 1} to ${Math.min(page * DEPARTMENT_PAGE_SIZE, filtered.length)} of ${filtered.length} departments`
                : '0 matching departments'}
        </p>
        <nav aria-label="Department pagination">
          <button
            type="button"
            aria-label="Previous department page"
            disabled={page <= 1 || loading}
            onClick={() => state.setPage(page - 1)}
          >
            <ChevronLeft aria-hidden="true" />
          </button>
          <span aria-current="page" aria-label={`Page ${page} of ${pages}`}>
            {page}
          </span>
          <button
            type="button"
            aria-label="Next department page"
            disabled={page >= pages || loading}
            onClick={() => state.setPage(page + 1)}
          >
            <ChevronRight aria-hidden="true" />
          </button>
        </nav>
      </footer>
    </section>
  )
}

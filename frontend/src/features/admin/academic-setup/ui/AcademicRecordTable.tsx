import { ChevronLeft, ChevronRight, MoreVertical, Plus, Search } from 'lucide-react'
import { label, records, usable } from '../academicSetupModel.ts'
import { entityIcons, entitySingular, entityTitles } from '../academicSetupPresentation.ts'
import type { AcademicDirectoryState } from '../useAcademicDirectory.ts'
import type { AcademicSetupState } from '../useAcademicSetup.ts'

export default function AcademicRecordTable({
  state,
  directory,
}: {
  state: AcademicSetupState
  directory: AcademicDirectoryState
}) {
  const { data, entity, definition, canManage, busy, formOpen, missing, open } = state
  if (!data) return null
  const Icon = entityIcons[entity]
  const { visible, filtered, selected, page, pages } = directory
  const relatedCount = (id: unknown) => records(data, 'programs').filter((row) => row.department_id === id).length
  return (
    <section className="academic-panel academic-directory" aria-label={`${entityTitles[entity]} directory`}>
      <div className="academic-panel-heading">
        <h2>
          <Icon aria-hidden="true" />
          {entityTitles[entity]}
          <span className="academic-count">{records(data, entity).length}</span>
        </h2>
        {canManage ? (
          <button
            type="button"
            className="academic-primary"
            disabled={busy || formOpen || missing.length > 0}
            aria-describedby={missing.length ? 'academic-prerequisites' : undefined}
            onClick={() => open(null)}
          >
            <Plus aria-hidden="true" />
            Add {entitySingular[entity]}
          </button>
        ) : (
          <span className="academic-muted">Read-only access</span>
        )}
      </div>
      <div className="academic-filters">
        <label className="academic-search">
          <Search aria-hidden="true" />
          <input
            aria-label={`Search ${entityTitles[entity].toLowerCase()}`}
            placeholder={`Search ${entityTitles[entity].toLowerCase()}…`}
            value={directory.search}
            onChange={(event) => directory.setSearch(event.target.value)}
          />
        </label>
        <select
          aria-label="Filter by status"
          value={directory.status}
          onChange={(event) => directory.setStatus(event.target.value)}
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive / unavailable</option>
        </select>
      </div>
      <div className="academic-table-scroll">
        <table className="academic-table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">{entitySingular[entity]} Name</th>
              <th scope="col">Code</th>
              {entity === 'departments' && data.records.programs !== undefined && <th scope="col">Programs</th>}
              <th scope="col">Status</th>
              {canManage && <th scope="col">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => {
              const id = String(row[definition.id])
              const active = usable(data, entity, row)
              return (
                <tr key={id} className={selected?.[definition.id] === row[definition.id] ? 'is-selected' : ''}>
                  <td>{(page - 1) * 6 + index + 1}</td>
                  <td>
                    <button
                      type="button"
                      className="academic-row-name"
                      aria-pressed={selected?.[definition.id] === row[definition.id]}
                      disabled={busy || formOpen}
                      onClick={() => directory.setSelectedId(id)}
                    >
                      {String(row.name ?? label(data, entity, row))}
                    </button>
                  </td>
                  <td>{String(row.code ?? '—')}</td>
                  {entity === 'departments' && data.records.programs !== undefined && (
                    <td>{relatedCount(row.department_id)}</td>
                  )}
                  <td>
                    <span
                      className={`academic-badge ${active ? 'is-active' : 'is-inactive'}`}
                      title={row.is_active && !active ? 'An academic parent is inactive or unavailable' : undefined}
                    >
                      {active ? 'Active' : row.is_active ? 'Unavailable' : 'Inactive'}
                    </span>
                    {row.is_current && <span className="academic-current">Current</span>}
                  </td>
                  {canManage && (
                    <td>
                      <button
                        type="button"
                        className="academic-row-action"
                        disabled={busy || formOpen}
                        aria-label={`Edit ${entity === 'batches' ? `${row.start_year}–${row.end_year}` : String(row.code ?? 'offering')}`}
                        title={`Edit ${entitySingular[entity].toLowerCase()}`}
                        onClick={() => {
                          directory.setSelectedId(id)
                          open(row)
                        }}
                      >
                        <MoreVertical aria-hidden="true" />
                      </button>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && (
        <p role="status" className="academic-empty">
          {records(data, entity).length
            ? 'No records match your filters.'
            : `No ${definition.label.toLowerCase()} have been entered. ${canManage ? (missing.length ? 'Follow the prerequisite steps below to continue.' : `Select Add ${entitySingular[entity]} to enter your college’s first record.`) : 'Ask an administrator with management access to add records.'}`}
        </p>
      )}
      <footer className="academic-pagination">
        <span>
          Showing {filtered.length ? (page - 1) * 6 + 1 : 0} to {Math.min(page * 6, filtered.length)} of{' '}
          {filtered.length} {entityTitles[entity].toLowerCase()}
        </span>
        <div>
          <button
            type="button"
            className="academic-icon-button"
            aria-label="Previous page"
            disabled={page <= 1 || formOpen}
            onClick={() => directory.setPage(page - 1)}
          >
            <ChevronLeft aria-hidden="true" />
          </button>
          <span className="academic-page-number" aria-label={`Page ${page} of ${pages}`}>
            {page}
          </span>
          <button
            type="button"
            className="academic-icon-button"
            aria-label="Next page"
            disabled={page >= pages || formOpen}
            onClick={() => directory.setPage(page + 1)}
          >
            <ChevronRight aria-hidden="true" />
          </button>
        </div>
      </footer>
    </section>
  )
}

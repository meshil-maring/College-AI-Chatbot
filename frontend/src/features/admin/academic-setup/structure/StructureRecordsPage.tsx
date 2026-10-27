import { useState, type ReactNode } from 'react'
import { ChevronRight, Eye, Pencil, Plus } from 'lucide-react'
import type { StructureEntity } from '../../../../types/academicStructure.ts'
import { useAcademicStructure, type StructureContext } from './useAcademicStructure.ts'
import { useStructureEditor } from './useStructureEditor.ts'
import StructureState from './StructureState.tsx'
import StructureDrawer from './StructureDrawer.tsx'
import { structureSingular, structureTitles, type StructureDraft } from './structureFields.ts'
import { structureId, type StructureRow } from './structureForm.ts'
import { structureContextLabel, structureLabel } from './structureLabels.ts'
import { structureCanEdit, structureCreationIssue } from './structureAvailability.ts'
import './styles/structure.css'

export default function StructureRecordsPage({
  context,
  entity,
  title,
  onOverview,
  children,
  defaults = {},
  filter,
}: {
  context: StructureContext
  entity: StructureEntity
  title?: string
  onOverview: () => void
  children?: ReactNode
  defaults?: StructureDraft
  filter?: (row: StructureRow) => boolean
}) {
  const state = useAcademicStructure(context)
  const creationIssue = structureCreationIssue(entity, state, defaults)
  const editor = useStructureEditor(state, entity, defaults)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [requestedPage, setPage] = useState(1)
  const available = state.structure?.records[entity]
  const records = (available ?? []).filter((row) => !filter || filter(row))
  const filtered = records
    .filter((row) =>
      `${structureLabel(entity, row, state)} ${structureContextLabel(row, state)} ${'code' in row ? row.code : ''}`
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
    )
    .filter((row) => !status || ('status' in row ? row.status === status : row.is_active === (status === 'active')))
  const pages = Math.max(1, Math.ceil(filtered.length / 10))
  const page = Math.min(requestedPage, pages)
  const rows = filtered.slice((page - 1) * 10, page * 10)
  const states = entity === 'curriculum_versions' ? ['draft', 'published', 'archived'] : ['active', 'inactive']
  return (
    <section className="academic-workspace structure-records-page" aria-label={`${structureTitles[entity]} management`}>
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">{title ?? structureTitles[entity]}</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>{title ?? structureTitles[entity]}</h1>
          <p>
            {entity === 'program_semesters'
              ? 'Define program progression separately from dated teaching terms.'
              : entity === 'academic_offerings'
                ? 'Deliver curriculum subjects within their assigned class sections.'
                : 'Manage versioned curricula and preserve the structures assigned to student batches.'}
          </p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canManage(entity) || editor.saving || Boolean(creationIssue)}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" />
          Add {structureSingular[entity]}
        </button>
      </header>
      <div className="structure-summary" aria-label="Academic record summary">
        <article>
          <span>Total {structureTitles[entity]}</span>
          <strong>{available ? records.length : '—'}</strong>
        </article>
        {states.map((value) => (
          <article key={value}>
            <span>{value}</span>
            <strong>
              {available
                ? records.filter((row) =>
                    'status' in row ? row.status === value : row.is_active === (value === 'active'),
                  ).length
                : '—'}
            </strong>
          </article>
        ))}
      </div>
      <StructureState state={state} />
      {!state.loading && state.canManage(entity) && creationIssue && <p role="status">{creationIssue}</p>}
      {children}
      {editor.notice && <p role="status">{editor.notice}</p>}
      <div className="structure-filters" role="search" aria-label="Filter academic records">
        <label>
          <span>Search</span>
          <input
            type="search"
            aria-label="Search academic records"
            placeholder="Search by name, code or program…"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </label>
        <label>
          <span>Status</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All Status</option>
            {states.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="structure-table-panel">
        <table className="structure-table">
          <caption className="sr-only">{structureTitles[entity]}</caption>
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Context</th>
              <th scope="col">{entity === 'curriculum_versions' ? 'Version' : 'Code / Type'}</th>
              <th scope="col">Status</th>
              <th scope="col">Updated</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => {
                const label = structureLabel(entity, row, state)
                return (
                  <tr key={structureId(entity, row)}>
                    <td data-label="Name">{label}</td>
                    <td data-label="Context">{structureContextLabel(row, state)}</td>
                    <td data-label="Code / Version">
                      {'version' in row
                        ? `v${row.version}`
                        : 'code' in row
                          ? row.code
                          : 'course_type' in row
                            ? row.course_type
                            : '—'}
                    </td>
                    <td data-label="Status">
                      <span
                        className={`structure-status ${'status' in row ? row.status : row.is_active ? 'active' : 'inactive'}`}
                      >
                        {'status' in row ? row.status : row.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td data-label="Updated">{new Date(row.updated_at).toLocaleDateString('en-IN')}</td>
                    <td>
                      <div className="structure-actions">
                        <button type="button" aria-label={`View ${label}`} onClick={() => editor.open('view', row)}>
                          <Eye aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          aria-label={`Edit ${label}`}
                          disabled={!structureCanEdit(entity, row, state) || editor.saving}
                          onClick={() => editor.open('edit', row)}
                        >
                          <Pencil aria-hidden="true" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={6}>
                  {state.loading
                    ? 'Loading…'
                    : available
                      ? 'No records found. Add a record or adjust the filters.'
                      : 'Records are unavailable.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <footer className="structure-pagination">
        <p role="status">
          Showing {filtered.length ? (page - 1) * 10 + 1 : 0} to {Math.min(page * 10, filtered.length)} of{' '}
          {filtered.length} records
        </p>
        <nav aria-label="Academic record pagination">
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            {page} / {pages}
          </span>
          <button type="button" disabled={page === pages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </nav>
      </footer>
      {editor.panel && <StructureDrawer editor={editor} entity={entity} />}
    </section>
  )
}

import { ArrowDown, ArrowUp, ArrowUpDown, SearchX } from 'lucide-react'
import type { SectionsState } from './useSections.ts'
import SectionRow, { type SectionActions } from './SectionRow.tsx'
import SectionPagination from './SectionPagination.tsx'

export default function SectionTable({
  state,
  onOpen,
  onDelete,
  deletionSaving,
}: { state: SectionsState } & SectionActions) {
  function sortable(label: string, field: 'name' | 'code' | 'status') {
    const sorted = state.sort.startsWith(`${field}-`)
    const descending = state.sort.endsWith('-desc')
    const Icon = sorted ? (descending ? ArrowDown : ArrowUp) : ArrowUpDown
    return (
      <th scope="col" aria-sort={sorted ? (descending ? 'descending' : 'ascending') : 'none'}>
        <button type="button" onClick={() => state.setSort(`${field}-${sorted && !descending ? 'desc' : 'asc'}`)}>
          {label}
          <Icon aria-hidden="true" />
        </button>
      </th>
    )
  }
  return (
    <section className="section-records" aria-label="Section records">
      <div className="section-table-panel">
        <table className="section-table">
          <caption className="sr-only">Institution sections</caption>
          <thead>
            <tr>
              {sortable('Section Name', 'name')}
              {sortable('Code', 'code')}
              <th scope="col">Batch</th>
              <th scope="col">Program</th>
              <th scope="col">Academic Year</th>
              <th scope="col">Student Count</th>
              {sortable('Status', 'status')}
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {state.rows.length ? (
              state.rows.map((record) => (
                <SectionRow
                  key={record.id}
                  record={record}
                  state={state}
                  onOpen={onOpen}
                  onDelete={onDelete}
                  deletionSaving={deletionSaving}
                />
              ))
            ) : (
              <tr>
                <td colSpan={8}>
                  <div className="section-empty">
                    <SearchX aria-hidden="true" />
                    <h2>No sections found</h2>
                    <p>Try a different search or add your first section.</p>
                    <button type="button" className="academic-secondary-button" onClick={state.clearFilters}>
                      Clear filters
                    </button>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <SectionPagination state={state} />
    </section>
  )
}

import { ArrowDown, ArrowUp, ArrowUpDown, SearchX } from 'lucide-react'
import type { BatchesState } from './useBatches.ts'
import BatchRow, { type BatchActions } from './BatchRow.tsx'
import BatchPagination from './BatchPagination.tsx'

export default function BatchTable({ state, onOpen }: { state: BatchesState } & BatchActions) {
  const sorted = state.sort.startsWith('name-')
  const descending = state.sort === 'name-desc'
  const SortIcon = sorted ? (descending ? ArrowDown : ArrowUp) : ArrowUpDown
  return (
    <section className="batch-records" aria-label="Batch records">
      <div className="batch-table-panel">
        <table className="batch-table">
          <caption className="sr-only">Institution batches</caption>
          <thead>
            <tr>
              <th scope="col" aria-sort={sorted ? (descending ? 'descending' : 'ascending') : 'none'}>
                <button type="button" onClick={() => state.setSort(sorted && !descending ? 'name-desc' : 'name-asc')}>
                  Batch Name
                  <SortIcon aria-hidden="true" />
                </button>
              </th>
              <th scope="col">Code</th>
              <th scope="col">Program</th>
              <th scope="col">Academic Year</th>
              <th scope="col">
                Curriculum
                <br />
                Version
              </th>
              <th scope="col">Student Count</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {state.rows.length ? (
              state.rows.map((record) => <BatchRow key={record.id} record={record} state={state} onOpen={onOpen} />)
            ) : (
              <tr>
                <td colSpan={8}>
                  <div className="batch-empty">
                    <SearchX aria-hidden="true" />
                    <h2>No batches found</h2>
                    <p>Try a different search or add your first batch after publishing a curriculum.</p>
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
      <BatchPagination state={state} />
    </section>
  )
}

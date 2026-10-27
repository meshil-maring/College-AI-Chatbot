import { Search, X } from 'lucide-react'
import type { BatchesState } from './useBatches.ts'
import type { BatchSort } from './batchModel.ts'

export default function BatchFilters({ state }: { state: BatchesState }) {
  return (
    <div className="batch-filters" role="search" aria-label="Filter batches">
      <label className="batch-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Search batches</span>
        <input
          type="search"
          value={state.search}
          onChange={(event) => state.setSearch(event.target.value)}
          placeholder="Search batches by name, code, or program..."
        />
        {state.search && (
          <button type="button" aria-label="Clear batch search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Program</span>
        <select value={state.program} onChange={(event) => state.setProgram(event.target.value)}>
          <option value="">All Programs</option>
          {state.programs.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Academic Year</span>
        <select value={state.year} onChange={(event) => state.setYear(event.target.value)}>
          <option value="">All Academic Years</option>
          {state.years.map((year) => (
            <option key={year.academic_year_id} value={year.academic_year_id}>
              {year.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Status</span>
        <select value={state.status} onChange={(event) => state.setStatus(event.target.value)}>
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>
      <label>
        <span>Sort by</span>
        <select value={state.sort} onChange={(event) => state.setSort(event.target.value as BatchSort)}>
          <option value="year-desc">Year (Newest)</option>
          <option value="year-asc">Year (Oldest)</option>
          <option value="name-asc">Name (A–Z)</option>
          <option value="name-desc">Name (Z–A)</option>
        </select>
      </label>
    </div>
  )
}

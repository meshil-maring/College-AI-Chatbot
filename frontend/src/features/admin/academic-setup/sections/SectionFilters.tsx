import { Search, X } from 'lucide-react'
import type { SectionsState } from './useSections.ts'
import type { SectionSort } from './sectionModel.ts'

export default function SectionFilters({ state }: { state: SectionsState }) {
  return (
    <div className="section-filters" role="search" aria-label="Filter sections">
      <label className="section-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Search sections</span>
        <input
          type="search"
          value={state.search}
          onChange={(event) => state.setSearch(event.target.value)}
          placeholder="Search sections by name or batch..."
        />
        {state.search && (
          <button type="button" aria-label="Clear section search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Batch</span>
        <select value={state.batch} onChange={(event) => state.setBatch(event.target.value)}>
          <option value="">All Batches</option>
          {state.batches.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
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
          <option value="">All Years</option>
          {state.yearLabels.map((year) => (
            <option key={year}>{year}</option>
          ))}
        </select>
      </label>
      <label>
        <span>Status</span>
        <select value={state.status} onChange={(event) => state.setStatus(event.target.value)}>
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>
      <label className="section-mobile-sort">
        <span>Sort by</span>
        <select value={state.sort} onChange={(event) => state.setSort(event.target.value as SectionSort)}>
          <option value="reference">Default order</option>
          <option value="name-asc">Name (A–Z)</option>
          <option value="name-desc">Name (Z–A)</option>
          <option value="code-asc">Code (A–Z)</option>
          <option value="code-desc">Code (Z–A)</option>
          <option value="status-asc">Status (Active first)</option>
          <option value="status-desc">Status (Inactive first)</option>
        </select>
      </label>
    </div>
  )
}

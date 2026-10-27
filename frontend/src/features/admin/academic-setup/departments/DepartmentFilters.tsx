import { Search, X } from 'lucide-react'
import type { useDepartments } from './useDepartments.ts'
import type { DepartmentSort, DepartmentStatus } from './departmentModel.ts'

export default function DepartmentFilters({ state }: { state: ReturnType<typeof useDepartments> }) {
  return (
    <div className="department-filters" role="search" aria-label="Search departments">
      <label className="department-search">
        <span className="sr-only">Search departments by name or code</span>
        <Search aria-hidden="true" />
        <input
          type="search"
          placeholder="Search departments by name or code…"
          value={state.search}
          onChange={(event) => state.setSearch(event.target.value)}
          disabled={!state.records || state.loading}
        />
        {state.search && (
          <button type="button" onClick={() => state.setSearch('')} aria-label="Clear department search">
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Status</span>
        <select
          value={state.status}
          onChange={(event) => state.setStatus(event.target.value as DepartmentStatus)}
          disabled={!state.records}
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>
      <label>
        <span>Sort by</span>
        <select
          value={state.sort}
          onChange={(event) => state.setSort(event.target.value as DepartmentSort)}
          disabled={!state.records}
        >
          <option value="name-asc">Name (A–Z)</option>
          <option value="name-desc">Name (Z–A)</option>
          <option value="code-asc">Code (A–Z)</option>
          <option value="code-desc">Code (Z–A)</option>
        </select>
      </label>
    </div>
  )
}

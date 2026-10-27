import { Search, X } from 'lucide-react'
import type { ProgramsState } from './usePrograms.ts'
import type { ProgramSort, ProgramStatus } from './programModel.ts'

export default function ProgramFilters({ state }: { state: ProgramsState }) {
  return (
    <div className="program-filters" role="search" aria-label="Filter programs">
      <label className="program-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Search programs</span>
        <input
          type="search"
          value={state.search}
          placeholder="Search programs by name or code..."
          onChange={(event) => state.setSearch(event.target.value)}
          disabled={!state.records}
        />
        {state.search && (
          <button type="button" aria-label="Clear program search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Department</span>
        <select
          value={state.department}
          onChange={(event) => state.setDepartment(event.target.value)}
          disabled={!state.departments}
        >
          <option value="">All Departments</option>
          {state.departments?.map((item) => (
            <option key={item.department_id} value={item.department_id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Degree Type</span>
        <select
          value={state.degree}
          onChange={(event) => state.setDegree(event.target.value)}
          disabled={!state.records}
        >
          <option value="">All Types</option>
          {state.degreeTypes.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </label>
      <label>
        <span>Status</span>
        <select
          value={state.status}
          onChange={(event) => state.setStatus(event.target.value as ProgramStatus)}
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
          onChange={(event) => state.setSort(event.target.value as ProgramSort)}
          disabled={!state.records}
        >
          <option value="name-asc">Name (A - Z)</option>
          <option value="name-desc">Name (Z - A)</option>
          <option value="code-asc">Code (A - Z)</option>
          <option value="code-desc">Code (Z - A)</option>
          <option value="department-asc">Department (A - Z)</option>
          <option value="department-desc">Department (Z - A)</option>
          <option value="degree_type-asc">Degree Type (A - Z)</option>
          <option value="degree_type-desc">Degree Type (Z - A)</option>
          <option value="duration_years-asc">Duration (Low - High)</option>
          <option value="duration_years-desc">Duration (High - Low)</option>
          <option value="total_credits-asc">Credits (Low - High)</option>
          <option value="total_credits-desc">Credits (High - Low)</option>
          <option value="is_active-asc">Status (Inactive first)</option>
          <option value="is_active-desc">Status (Active first)</option>
        </select>
      </label>
    </div>
  )
}

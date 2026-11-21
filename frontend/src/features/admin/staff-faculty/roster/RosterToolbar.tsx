import { Search } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import { BUTTON_CLASS, SELECT_CLASS } from '../StaffFacultyUI.tsx'
import { NO_DEPARTMENT, type RoleFilter, type RosterFilters, type StatusFilter } from './useRosterFilters.ts'

/** Search and filters for the roster. Results update as the administrator types. */
export default function RosterToolbar({
  filters,
  departments,
  total,
}: {
  filters: RosterFilters
  departments: Department[]
  total: number
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 md:flex-row md:flex-wrap md:items-center">
        <label className="relative flex-1 md:min-w-64">
          <span className="sr-only">Search staff and faculty</span>
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted"
          />
          <input
            type="search"
            value={filters.search}
            onChange={(event) => filters.setSearch(event.target.value)}
            placeholder="Search by name, email or department"
            className={`${SELECT_CLASS} w-full pl-9`}
          />
        </label>
        <select
          aria-label="Filter by role"
          value={filters.role}
          onChange={(event) => filters.setRole(event.target.value as RoleFilter)}
          className={SELECT_CLASS}
        >
          <option value="all">All roles</option>
          <option value="faculty">Faculty (Teacher) only</option>
          <option value="staff">Staff only</option>
        </select>
        <select
          aria-label="Filter by status"
          value={filters.status}
          onChange={(event) => filters.setStatus(event.target.value as StatusFilter)}
          className={SELECT_CLASS}
        >
          <option value="all">Any status</option>
          <option value="active">Active</option>
          <option value="inactive">Deactivated</option>
        </select>
        <select
          aria-label="Filter by department"
          value={filters.department}
          onChange={(event) => filters.setDepartment(event.target.value)}
          className={SELECT_CLASS}
        >
          <option value="all">All departments</option>
          <option value={NO_DEPARTMENT}>No department yet</option>
          {departments.map((department) => (
            <option key={department.department_id} value={department.department_id}>
              {department.name}
            </option>
          ))}
        </select>
        {filters.filtered ? (
          <button type="button" onClick={filters.clear} className={BUTTON_CLASS}>
            Clear filters
          </button>
        ) : null}
      </div>
      <p className="text-xs text-muted" aria-live="polite">
        {filters.filtered ? `Showing ${filters.visible.length} of ` : null}
        {total} {total === 1 ? 'member' : 'members'}
      </p>
    </div>
  )
}

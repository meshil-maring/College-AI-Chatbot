import { Search, X } from 'lucide-react'
import type { CalendarState } from './useCalendar.ts'
import type { CalendarSort, CalendarStatus } from './calendarModel.ts'

export default function CalendarFilters({ state }: { state: CalendarState }) {
  return (
    <div className="calendar-filters">
      <div className="calendar-search">
        <Search aria-hidden="true" />
        <input
          type="search"
          aria-label="Search academic calendar"
          placeholder={state.tab === 'semesters' ? 'Search semesters...' : 'Search academic years...'}
          value={state.search}
          onChange={(event) => state.setSearch(event.target.value)}
        />
        {state.search && (
          <button type="button" aria-label="Clear search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </div>
      <label>
        Status
        <select value={state.status} onChange={(event) => state.setStatus(event.target.value as CalendarStatus)}>
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="upcoming">Upcoming</option>
          <option value="completed">Completed</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>
      <label>
        Sort by
        <select value={state.sort} onChange={(event) => state.setSort(event.target.value as CalendarSort)}>
          <option value="newest">Year (Newest)</option>
          <option value="oldest">Year (Oldest)</option>
          <option value="name">Name (A–Z)</option>
        </select>
      </label>
    </div>
  )
}

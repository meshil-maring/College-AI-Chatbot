import { ChevronLeft, ChevronRight } from 'lucide-react'
import { CALENDAR_PAGE_SIZE } from './calendarModel.ts'
import type { CalendarState } from './useCalendar.ts'

export default function CalendarPagination({ state }: { state: CalendarState }) {
  return (
    <nav className="calendar-pagination" aria-label="Calendar pagination">
      <p>
        Showing {state.count ? (state.page - 1) * CALENDAR_PAGE_SIZE + 1 : 0} to{' '}
        {Math.min(state.page * CALENDAR_PAGE_SIZE, state.count)} of {state.count}{' '}
        {state.tab === 'semesters' ? 'semesters' : 'academic years'}
      </p>
      <div>
        <button
          type="button"
          aria-label="Previous page"
          disabled={state.page <= 1}
          onClick={() => state.setPage(state.page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
        </button>
        <span aria-current="page" aria-label={`Page ${state.page} of ${state.pages}`}>
          {state.page}
        </span>
        <button
          type="button"
          aria-label="Next page"
          disabled={state.page >= state.pages}
          onClick={() => state.setPage(state.page + 1)}
        >
          <ChevronRight aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}

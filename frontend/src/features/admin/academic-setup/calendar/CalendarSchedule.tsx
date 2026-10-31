import { CalendarDays } from 'lucide-react'
import type { CalendarState } from './useCalendar.ts'
import { formatCalendarDate, localDate, periodStatus } from './calendarModel.ts'
import CalendarActions from './CalendarActions.tsx'
import type { CalendarEditor } from './useCalendarEditor.ts'
import type { CalendarDeletion } from './useCalendarDeletion.ts'

export default function CalendarSchedule({
  state,
  editor,
  deletion,
}: {
  state: CalendarState
  editor: CalendarEditor
  deletion: CalendarDeletion
}) {
  if (state.tab === 'dates') {
    const periods = state.filteredYears.flatMap((year) => [
      year,
      ...(state.semesters ?? []).filter((semester) => semester.academic_year_id === year.academic_year_id),
    ])
    const events = periods
      .flatMap((period) => [
        { period, date: period.start_date, label: 'begins' },
        { period, date: period.end_date, label: 'ends' },
      ])
      .sort((a, b) => a.date.localeCompare(b.date))
    return (
      <section className="calendar-dates" aria-label="Important academic dates">
        <p className="calendar-schedule-note">Start and end dates from your academic years and semesters.</p>
        {events.map(({ period, date, label }) => (
          <article key={`${'semester_id' in period ? period.semester_id : period.academic_year_id}-${label}`}>
            <span className="calendar-date-icon">
              <CalendarDays aria-hidden="true" />
            </span>
            <time dateTime={date}>{formatCalendarDate(date)}</time>
            <div>
              <strong>
                {period.name} {label}
              </strong>
              <small>
                {'semester_id' in period ? 'Semester' : 'Academic year'} · {period.code}
              </small>
            </div>
            <CalendarActions
              record={period}
              editor={editor}
              deletion={deletion}
              canEdit={!state.busy && ('semester_id' in period ? state.canManageSemesters : state.canManageYears)}
            />
          </article>
        ))}
      </section>
    )
  }
  const today = localDate()
  return (
    <section className="calendar-timeline" aria-label="Academic calendar timeline">
      <p className="calendar-schedule-note">
        Academic years and their dated semesters. Today: {formatCalendarDate(today)}.
      </p>
      {state.filteredYears.map((year) => {
        const start = Date.parse(year.start_date)
        const duration = Math.max(1, Date.parse(year.end_date) - start)
        const position = (value: string) => Math.max(0, Math.min(100, ((Date.parse(value) - start) / duration) * 100))
        return (
          <article key={year.academic_year_id}>
            <header>
              <h2>{year.name}</h2>
              <span>
                {formatCalendarDate(year.start_date)} — {formatCalendarDate(year.end_date)}
              </span>
            </header>
            <div className="calendar-timeline-track" aria-label={`${year.name} semesters`}>
              {today >= year.start_date && today <= year.end_date && (
                <span className="calendar-today-marker" style={{ left: `${position(today)}%` }} title="Today" />
              )}
              {state.semesters
                ?.filter((semester) => semester.academic_year_id === year.academic_year_id)
                .map((semester) => (
                  <button
                    type="button"
                    key={semester.semester_id}
                    className={`calendar-timeline-bar ${periodStatus(semester)}`}
                    style={{
                      marginLeft: `${position(semester.start_date)}%`,
                      width: `${Math.max(1, position(semester.end_date) - position(semester.start_date))}%`,
                    }}
                    title={`${semester.name}: ${formatCalendarDate(semester.start_date)} to ${formatCalendarDate(semester.end_date)}`}
                    onClick={() => editor.open('semesters', 'view', semester)}
                  >
                    {semester.name}
                  </button>
                ))}
            </div>
            {!state.semesters && <p className="calendar-inline-empty">Semester records are unavailable.</p>}
          </article>
        )
      })}
    </section>
  )
}

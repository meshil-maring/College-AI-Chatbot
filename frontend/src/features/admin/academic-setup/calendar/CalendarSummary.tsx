import { BookOpen, CalendarDays, Circle } from 'lucide-react'
import type { CalendarState } from './useCalendar.ts'
import { semesterType } from './calendarModel.ts'

export default function CalendarSummary({ state }: { state: CalendarState }) {
  const currentYears = state.years?.filter((year) => year.is_active && year.is_current)
  const currentSemesters = state.semesters?.filter((semester) => semester.is_active && semester.is_current)
  const metrics = [
    { label: 'Total Academic Years', value: state.years?.length, icon: CalendarDays },
    {
      label: 'Active Academic Year',
      value: currentYears?.length,
      icon: Circle,
      detail: currentYears?.map((year) => year.name).join(', '),
      tone: 'active',
    },
    { label: 'Total Semesters', value: state.semesters?.length, icon: BookOpen },
    {
      label: 'Ongoing Semester',
      value: currentSemesters?.length,
      icon: CalendarDays,
      detail: currentSemesters
        ?.map((semester) => `${semester.name} (${semesterType(semester.semester_number)})`)
        .join(', '),
    },
  ]
  return (
    <section className="calendar-summary" aria-label="Academic calendar summary" aria-busy={state.loading}>
      {metrics.map(({ label, value, icon: Icon, detail, tone }) => (
        <article className="calendar-metric" key={label}>
          <span className={`calendar-metric-icon ${tone ?? ''}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            {state.loading ? (
              <strong className="calendar-skeleton" aria-label="Loading" />
            ) : (
              <strong>{value ?? '—'}</strong>
            )}
            {!state.loading && <small>{value === undefined ? 'Unavailable' : detail}</small>}
          </div>
        </article>
      ))}
    </section>
  )
}

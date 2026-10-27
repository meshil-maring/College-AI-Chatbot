import { BookOpen, Circle, CalendarDays } from 'lucide-react'
import type { SubjectsState } from './useSubjects.ts'

export default function SubjectSummary({ state }: { state: SubjectsState }) {
  const metrics = [
    { label: 'Total Subjects', value: state.records?.length, icon: BookOpen, tone: 'total' },
    {
      label: 'Active Subjects',
      value: state.records?.filter((item) => item.is_active).length,
      icon: Circle,
      tone: 'active',
    },
    {
      label: 'Inactive Subjects',
      value: state.records?.filter((item) => !item.is_active).length,
      icon: Circle,
      tone: 'inactive',
    },
    { label: 'Departments', value: state.departments?.length, icon: CalendarDays, tone: 'departments' },
  ]
  return (
    <section className="subject-summary" aria-label="Subject summary" aria-busy={state.loading}>
      {metrics.map(({ label, value, icon: Icon, tone }) => (
        <article className="subject-metric" key={label}>
          <span className={`subject-metric-icon ${tone}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            {state.loading ? (
              <strong className="subject-skeleton" aria-label="Loading" />
            ) : (
              <strong>{value ?? '—'}</strong>
            )}
            {!state.loading && value === undefined && <small>Unavailable</small>}
          </div>
        </article>
      ))}
    </section>
  )
}

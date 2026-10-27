import { Circle, GraduationCap, Users } from 'lucide-react'
import type { ProgramsState } from './usePrograms.ts'

export default function ProgramSummary({ state }: { state: ProgramsState }) {
  const metrics = [
    { label: 'Total Programs', value: state.records?.length, icon: GraduationCap, tone: 'total' },
    {
      label: 'Active Programs',
      value: state.records?.filter((item) => item.is_active).length,
      icon: Circle,
      tone: 'active',
    },
    {
      label: 'Inactive Programs',
      value: state.records?.filter((item) => !item.is_active).length,
      icon: Circle,
      tone: 'inactive',
    },
    { label: 'Departments', value: state.departments?.length, icon: Users, tone: 'departments' },
  ]
  return (
    <section className="program-summary" aria-label="Program summary" aria-busy={state.loading}>
      {metrics.map(({ label, value, icon: Icon, tone }) => (
        <article className="program-metric" key={label}>
          <span className={`program-metric-icon ${tone}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            {state.loading ? (
              <strong className="program-skeleton" aria-label="Loading" />
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

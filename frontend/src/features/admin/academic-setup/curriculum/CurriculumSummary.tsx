import { Circle, FileText, Users } from 'lucide-react'
import type { CurriculumState } from './useCurriculum.ts'

export default function CurriculumSummary({ state }: { state: CurriculumState }) {
  const programIds = new Set(state.programs?.map((program) => program.program_id))
  const programCount =
    state.programs && state.links
      ? new Set(state.links.filter((link) => programIds.has(link.program_id)).map((link) => link.program_id)).size
      : undefined
  const metrics = [
    {
      label: 'Total Curricula',
      icon: FileText,
      tone: 'total',
      value: undefined,
      note: 'Version storage not connected',
    },
    { label: 'Active Curricula', icon: Circle, tone: 'active', value: undefined, note: 'Lifecycle not connected' },
    { label: 'Inactive Curricula', icon: Circle, tone: 'inactive', value: undefined, note: 'Archive not connected' },
    { label: 'Programs', icon: Users, tone: 'programs', value: programCount, note: 'With subject mappings' },
  ]
  return (
    <section className="curriculum-summary" aria-label="Curriculum summary" aria-busy={state.loading}>
      {metrics.map(({ label, icon: Icon, tone, value, note }) => (
        <article className="curriculum-metric" key={label}>
          <span className={`curriculum-metric-icon ${tone}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            {state.loading ? (
              <strong className="curriculum-skeleton" aria-label="Loading" />
            ) : (
              <strong>{value ?? '—'}</strong>
            )}
            <small>{note}</small>
          </div>
        </article>
      ))}
    </section>
  )
}

import { Circle, UsersRound } from 'lucide-react'
import type { SectionRecord } from './sectionModel.ts'

export default function SectionSummary({ records, available }: { records: SectionRecord[]; available: boolean }) {
  const active = records.filter((item) => item.status === 'active').length
  const metrics = [
    { label: 'Total Sections', value: records.length, help: 'Across all batches', Icon: UsersRound, style: 'total' },
    { label: 'Active Sections', value: active, help: 'Currently active', Icon: Circle, style: 'active' },
    {
      label: 'Inactive Sections',
      value: records.length - active,
      help: 'Temporarily disabled',
      Icon: Circle,
      style: 'inactive',
    },
    {
      label: 'Total Students',
      value: undefined,
      help: 'Enrollment data unavailable',
      Icon: UsersRound,
      style: 'total',
    },
  ]
  return (
    <section className="section-summary" aria-label="Section summary">
      {metrics.map(({ label, value, help, Icon, style }) => (
        <article className="section-metric" key={label} aria-label={label}>
          <span className={`section-metric-icon ${style}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            <strong>{available ? (value?.toLocaleString('en-IN') ?? '—') : '—'}</strong>
            <small>{help}</small>
          </div>
        </article>
      ))}
    </section>
  )
}

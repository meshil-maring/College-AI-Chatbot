import { Circle, UserRound, UsersRound } from 'lucide-react'
import type { BatchRecord } from './batchModel.ts'

export default function BatchSummary({ records, available }: { records: BatchRecord[]; available: boolean }) {
  const active = records.filter((item) => item.status === 'active').length
  const metrics = [
    { label: 'Total Batches', value: records.length, help: 'Across all programs', Icon: UsersRound, style: 'total' },
    { label: 'Active Batches', value: active, help: 'Currently active', Icon: Circle, style: 'active' },
    {
      label: 'Inactive Batches',
      value: records.length - active,
      help: 'Completed or inactive',
      Icon: Circle,
      style: 'inactive',
    },
    {
      label: 'Total Students',
      value: undefined,
      help: 'Enrollment data unavailable',
      Icon: UserRound,
      style: 'total',
    },
  ]
  return (
    <section className="batch-summary" aria-label="Batch summary">
      {metrics.map(({ label, value, help, Icon, style }) => (
        <article className="batch-metric" key={label} aria-label={label}>
          <span className={`batch-metric-icon ${style}`}>
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

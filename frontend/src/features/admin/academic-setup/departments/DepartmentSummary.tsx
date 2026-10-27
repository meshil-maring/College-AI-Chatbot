import { Building2, CircleCheck, CirclePause } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'

export default function DepartmentSummary({ records, loading }: { records?: Department[]; loading: boolean }) {
  const metrics = [
    { label: 'Total Departments', count: records?.length, Icon: Building2, tone: 'total' },
    {
      label: 'Active Departments',
      count: records?.filter((record) => record.is_active).length,
      Icon: CircleCheck,
      tone: 'active',
    },
    {
      label: 'Inactive Departments',
      count: records?.filter((record) => !record.is_active).length,
      Icon: CirclePause,
      tone: 'inactive',
    },
  ]
  return (
    <section className="department-summary" aria-label="Department summary" aria-busy={loading}>
      {metrics.map(({ label, count, Icon, tone }) => (
        <article className="department-metric" key={label}>
          <span className={`department-metric-icon ${tone}`}>
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p>{label}</p>
            <strong className={loading ? 'department-skeleton' : undefined}>
              {loading ? <span className="sr-only">Loading</span> : (count ?? '—')}
            </strong>
            {count === undefined && <small>{loading ? 'Loading…' : 'Not connected'}</small>}
          </div>
        </article>
      ))}
    </section>
  )
}

import { Clock, MailCheck, MailWarning, UsersRound } from 'lucide-react'
import type { InvitationFilter } from './invitationFilters.ts'

const METRICS = [
  { filter: 'all', label: 'Awaiting account setup', tone: '', Icon: UsersRound },
  { filter: 'sent', label: 'Setup emails delivered', tone: 'is-success', Icon: MailCheck },
  { filter: 'failed', label: 'Email delivery issues', tone: 'is-warning', Icon: MailWarning },
  { filter: 'expired', label: 'Expired setup links', tone: 'is-danger', Icon: Clock },
] as const

/** Delivery summary for unaccepted invitations; each card filters the table below. */
export default function InvitationMetrics({
  counts,
  unavailable,
  filter,
  onFilter,
}: {
  counts: Record<InvitationFilter, number>
  unavailable: boolean
  filter: InvitationFilter
  onFilter: (filter: InvitationFilter) => void
}) {
  return (
    <div className="student-onboarding-metrics" role="group" aria-label="Filter invitations by status">
      {METRICS.map(({ filter: value, label, tone, Icon }) => (
        <button
          key={value}
          type="button"
          className={`student-onboarding-metric ${tone}`.trim()}
          aria-pressed={filter === value}
          disabled={unavailable}
          onClick={() => onFilter(filter === value ? 'all' : value)}
        >
          <span className="student-onboarding-metric-icon">
            <Icon size={20} aria-hidden="true" />
          </span>
          <span>
            <strong>{unavailable ? '—' : counts[value]}</strong>
            <span>{label}</span>
          </span>
        </button>
      ))}
    </div>
  )
}

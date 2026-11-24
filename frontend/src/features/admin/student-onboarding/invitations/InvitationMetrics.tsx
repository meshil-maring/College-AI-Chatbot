import { MailCheck, MailWarning, UsersRound } from 'lucide-react'
import type { StudentInvitation } from '../../../../types/admin/students.ts'

/** Summary of setup-link delivery for invitations that have not been accepted yet. */
export default function InvitationMetrics({
  invitations,
  unavailable,
}: {
  invitations: StudentInvitation[]
  unavailable: boolean
}) {
  const sent = invitations.filter((invitation) => invitation.email_delivery_status === 'sent').length
  const issues = invitations.filter((invitation) => invitation.email_delivery_status === 'failed').length
  const metrics = [
    { label: 'Awaiting account setup', value: invitations.length, tone: '', Icon: UsersRound },
    { label: 'Setup emails delivered', value: sent, tone: 'is-success', Icon: MailCheck },
    { label: 'Email delivery issues', value: issues, tone: 'is-warning', Icon: MailWarning },
  ]
  return (
    <div className="student-onboarding-metrics" aria-label="Invitation summary">
      {metrics.map(({ label, value, tone, Icon }) => (
        <article key={label} className={`student-onboarding-metric ${tone}`.trim()}>
          <span className="student-onboarding-metric-icon">
            <Icon size={20} aria-hidden="true" />
          </span>
          <div>
            <strong>{unavailable ? '—' : value}</strong>
            <span>{label}</span>
          </div>
        </article>
      ))}
    </div>
  )
}

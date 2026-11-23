import { Mail, RotateCw } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MemberInvitation } from '../../../../types/admin.ts'
import {
  Badge,
  BUTTON_CLASS,
  DANGER_BUTTON_CLASS,
  formatDate,
  Initials,
  roleLabel,
  StatusBadge,
} from '../StaffFacultyUI.tsx'
import type { MemberInvitationsModel } from './useMemberInvitations.ts'

const DELIVERY: Record<string, string> = {
  pending: 'Email queued',
  sent: 'Email sent',
  failed: 'Email failed — resend it',
}

/** Invitations waiting for the person to accept, with resend, cancel and invite-again actions. */
export default function PendingInvitations({
  model,
  departments,
  onInviteAgain,
}: {
  model: MemberInvitationsModel
  departments: Department[]
  onInviteAgain: (invitation: MemberInvitation) => void
}) {
  const { invitations, loading, loadError, actionKey, error } = model
  const busy = actionKey !== null
  const departmentName = (id: string | null) =>
    departments.find((department) => department.department_id === id)?.name ?? 'Department no longer active'

  return (
    <section
      aria-labelledby="member-invitations-heading"
      className="space-y-4 rounded-xl border border-line bg-surface p-4"
    >
      <div>
        <h2 id="member-invitations-heading" className="sr-only">
          Pending invitations
        </h2>
        <p className="mt-1 max-w-[70ch] text-sm text-muted">
          People you invited appear on the roster after they accept. Links expire after 24 hours; resend a link if it
          was lost, or invite again once it expires.
        </p>
      </div>
      {error || loadError ? (
        <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
          {error ?? loadError}
        </p>
      ) : null}
      {loading ? (
        <p role="status" className="text-sm text-muted">
          Loading invitations…
        </p>
      ) : invitations.length === 0 ? (
        <p className="flex items-center gap-2 py-4 text-sm text-muted">
          <Mail aria-hidden="true" className="size-4" />
          No invitations waiting. Use Add member to invite Staff or Faculty by email.
        </p>
      ) : (
        <ul className="space-y-3">
          {invitations.map((invitation) => {
            const label = invitation.full_name || invitation.email
            const expired = invitation.status === 'expired'
            const expires = formatDate(invitation.expires_at)
            return (
              <li
                key={invitation.invitation_id}
                className="flex flex-col gap-3 rounded-xl border border-line p-4 md:flex-row md:items-center"
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <Initials name={label} />
                  <div className="min-w-0 space-y-1">
                    <p className="font-semibold text-content">{invitation.full_name || 'Unnamed'}</p>
                    <p className="break-all text-sm text-muted">{invitation.email}</p>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                      <StatusBadge status={expired ? 'expired' : 'pending'} />
                      <Badge tone="info">{roleLabel(invitation.role)}</Badge>
                      <span>{departmentName(invitation.department_id)}</span>
                      {expires ? <span>{expired ? `Expired ${expires}` : `Expires ${expires}`}</span> : null}
                      {!expired ? (
                        <span>{DELIVERY[invitation.email_delivery_status] ?? 'Email status unknown'}</span>
                      ) : null}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {expired ? (
                    <button
                      type="button"
                      disabled={busy}
                      aria-label={`Invite ${label} again`}
                      onClick={() => onInviteAgain(invitation)}
                      className={BUTTON_CLASS}
                    >
                      Invite again
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        disabled={busy}
                        aria-label={`Resend invitation to ${label}`}
                        onClick={() => void model.resend(invitation)}
                        className={BUTTON_CLASS}
                      >
                        <RotateCw aria-hidden="true" className="size-4" />
                        {actionKey === `resend:${invitation.invitation_id}` ? 'Resending…' : 'Resend'}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        aria-label={`Cancel invitation for ${label}`}
                        onClick={() => void model.cancel(invitation)}
                        className={DANGER_BUTTON_CLASS}
                      >
                        {actionKey === `cancel:${invitation.invitation_id}` ? 'Cancelling…' : 'Cancel'}
                      </button>
                    </>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

import type { AdminRosterEntry } from '../../../types/platform.ts'

export function statusLabel(status: string): string {
  if (status === 'invited') return 'Invited'
  if (status === 'cancelled') return 'Cancelled'
  if (status === 'expired') return 'Expired'
  return 'Active'
}

/**
 * Phase 7.15 — the invitation's EMAIL state, shown separately from its
 * lifecycle state.
 *
 * A failed delivery is the single most actionable thing on this screen: the
 * invitation is still live and still acceptable, but the invited person never
 * received the link, so it needs a Resend. Showing that honestly — instead of a
 * bare "Invited" — is the whole point of tracking delivery server-side.
 */
export function deliveryLabel(status: string | null, attempts: number | null): string {
  if (status === 'failed') {
    return attempts !== null && attempts > 0
      ? `Email not sent (${attempts} attempt${attempts === 1 ? '' : 's'})`
      : 'Email not sent'
  }
  if (status === 'delivered') return 'Email delivered'
  if (status === 'sent') return 'Email sent'
  return 'Email pending'
}

export function deliveryClass(status: string | null): string {
  if (status === 'failed') return 'text-rose-300'
  if (status === 'sent' || status === 'delivered') return 'text-emerald-300'
  return 'text-slate-400'
}

export function expiryLabel(expiresAt: string | null): string {
  if (expiresAt === null) return ''
  const parsed = new Date(expiresAt)
  if (Number.isNaN(parsed.getTime())) return ''
  return `Expires: ${parsed.toLocaleString()}`
}

/**
 * The roster table: accepted admins (Revoke) and invitations (Resend / Cancel).
 *
 * Phase 7.15 adds the invitation's EMAIL state and a Resend action. Resend is
 * offered for a PENDING invitation and for an EXPIRED one (whose operator
 * needs a fresh link to reach the invitee); it is deliberately NOT offered for
 * a CANCELLED invitation, because reissuing a deliberately cancelled
 * invitation would undo an explicit operator decision.
 *
 * Only platform-administration fields are shown — email, lifecycle status,
 * email delivery state and the expiry. No password, token, token hash, name
 * record or student data exists in these rows; the roster response model has
 * no such fields, so nothing here can leak them by accident.
 */
export function RosterTable({
  roster,
  institutionCode,
  busy,
  onCancel,
  onResend,
  onRevoke,
}: {
  roster: {
    admins: readonly AdminRosterEntry[]
    pending_invitations: readonly AdminRosterEntry[]
    admin_count: number
  }
  institutionCode: string
  busy: 'invite' | 'cancel' | 'resend' | 'revoke' | null
  onCancel: (entry: AdminRosterEntry) => void
  onResend: (entry: AdminRosterEntry) => void
  onRevoke: (entry: AdminRosterEntry) => void
}) {
  if (roster.admins.length === 0 && roster.pending_invitations.length === 0) {
    return (
      <p className="mt-4 rounded-xl border border-slate-700 bg-slate-950 px-5 py-6 text-center text-sm text-slate-400">
        No University Admins yet. Use &quot;+ Invite Admin&quot; to invite the first one.
      </p>
    )
  }
  return (
    <>
      <p className="mt-4 text-sm text-slate-400">
        {roster.admin_count} active {roster.admin_count === 1 ? 'admin' : 'admins'} for {institutionCode}.
      </p>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">University Admins and pending invitations for {institutionCode}</caption>
        <thead className="border-b border-slate-700 bg-slate-800/60 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" className="px-4 py-3 font-semibold">
              Email
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              Status
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {roster.admins.map((entry) => (
            <tr key={`admin-${entry.user_id ?? entry.email}`} className="border-b border-slate-800">
              <td className="px-4 py-3 text-slate-200">{entry.email}</td>
              <td className="px-4 py-3 text-slate-300">Active</td>
              <td className="px-4 py-3">
                <button
                  type="button"
                  onClick={() => onRevoke(entry)}
                  disabled={busy !== null || entry.user_id === null}
                  className="rounded-lg border border-rose-500/50 px-3 py-1.5 text-xs font-medium text-rose-200 hover:bg-rose-500/10 focus:outline-none focus:ring-2 focus:ring-rose-300 disabled:opacity-50"
                >
                  Revoke
                </button>
              </td>
            </tr>
          ))}
          {roster.pending_invitations.map((entry) => (
            <tr key={`invite-${entry.invitation_id ?? entry.email}`} className="border-b border-slate-800">
              <td className="px-4 py-3 text-slate-200">{entry.email}</td>
              <td className="px-4 py-3">
                <div className="text-slate-300">{statusLabel(entry.status)}</div>
                <div className={`mt-0.5 text-xs ${deliveryClass(entry.email_delivery_status)}`}>
                  {deliveryLabel(entry.email_delivery_status, entry.email_delivery_attempts)}
                </div>
                {expiryLabel(entry.expires_at) !== '' ? (
                  <div className="mt-0.5 text-xs text-slate-500">{expiryLabel(entry.expires_at)}</div>
                ) : null}
                {entry.resend_count !== null && entry.resend_count > 0 ? (
                  <div className="mt-0.5 text-xs text-slate-500">Resent {entry.resend_count}&times;</div>
                ) : null}
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  {entry.invitation_id !== null && (entry.status === 'invited' || entry.status === 'expired') ? (
                    <button
                      type="button"
                      disabled={busy !== null}
                      onClick={() => onResend(entry)}
                      className="rounded-lg border border-violet-500/60 px-3 py-1.5 text-xs font-medium text-violet-100 hover:bg-violet-500/20 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
                    >
                      {busy === 'resend' ? 'Resending...' : 'Resend'}
                    </button>
                  ) : null}
                  {entry.status === 'invited' && entry.invitation_id !== null ? (
                    <button
                      type="button"
                      disabled={busy !== null}
                      onClick={() => onCancel(entry)}
                      className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50"
                    >
                      {busy === 'cancel' ? 'Cancelling...' : 'Cancel'}
                    </button>
                  ) : (
                    <span className="text-xs text-slate-500">No action</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

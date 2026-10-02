import type { AdminInvitationCreated, AdminInvitationResend, AdminRosterEntry } from '../../types/platform.ts'

/**
 * The one-time invitation link reveal.
 *
 * The raw link is displayed exactly once, right after creation, purely so the
 * operator can deliver it. It is NOT a secret the platform stores: the backend
 * kept only a SHA-256 digest, so this value can never be re-fetched. That is
 * why the copy is an explicit, user-initiated action rather than an automatic
 * clipboard write — the operator is told plainly that losing it means
 * cancelling and reissuing.
 *
 * No token hash, backend secret or password is ever rendered here; the backend
 * response model has no such fields to render.
 */
export function InvitationLinkNotice({
  created,
  copied,
  setCopied,
  onDone,
}: {
  created: AdminInvitationCreated | AdminInvitationResend
  copied: boolean
  setCopied: (value: boolean) => void
  onDone: () => void
}) {
  const link = `${window.location.origin}${created.invitation_url}`
  return (
    <div className="mt-4 rounded-xl border border-violet-500/40 bg-violet-500/10 p-4">
      <p className="text-sm font-semibold text-violet-100">
        Invitation link for {created.invitation.email}
      </p>
      <p className="mt-1 text-xs text-violet-200">
        This link is shown only once and expires in {created.expires_in_hours} hours. Copy it
        now — it cannot be retrieved again.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <code
          data-testid="invitation-link"
          className="max-w-full break-all rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300"
        >
          {link}
        </code>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard?.writeText(link).then(() => setCopied(true))
          }}
          className="rounded-lg border border-violet-400 px-3 py-2 text-xs font-medium text-violet-100 hover:bg-violet-500/20 focus:outline-none focus:ring-2 focus:ring-violet-300"
        >
          {copied ? 'Copied' : 'Copy link'}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-lg border border-slate-600 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          Done
        </button>
      </div>
    </div>
  )
}

function statusLabel(status: string): string {
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
function deliveryLabel(status: string | null, attempts: number | null): string {
  if (status === 'failed') {
    return attempts !== null && attempts > 0
      ? `Email not sent (${attempts} attempt${attempts === 1 ? '' : 's'})`
      : 'Email not sent'
  }
  if (status === 'delivered') return 'Email delivered'
  if (status === 'sent') return 'Email sent'
  return 'Email pending'
}

function deliveryClass(status: string | null): string {
  if (status === 'failed') return 'text-rose-300'
  if (status === 'sent' || status === 'delivered') return 'text-emerald-300'
  return 'text-slate-400'
}

function expiryLabel(expiresAt: string | null): string {
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
        {roster.admin_count} active {roster.admin_count === 1 ? 'admin' : 'admins'} for{' '}
        {institutionCode}.
      </p>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">
          University Admins and pending invitations for {institutionCode}
        </caption>
        <thead className="border-b border-slate-700 bg-slate-800/60 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" className="px-4 py-3 font-semibold">Email</th>
            <th scope="col" className="px-4 py-3 font-semibold">Status</th>
            <th scope="col" className="px-4 py-3 font-semibold">Actions</th>
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
                  <div className="mt-0.5 text-xs text-slate-500">
                    {expiryLabel(entry.expires_at)}
                  </div>
                ) : null}
                {entry.resend_count !== null && entry.resend_count > 0 ? (
                  <div className="mt-0.5 text-xs text-slate-500">
                    Resent {entry.resend_count}&times;
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  {entry.invitation_id !== null &&
                  (entry.status === 'invited' || entry.status === 'expired') ? (
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

/**
 * Explicit confirmation before a Resend, because it destroys something.
 *
 * Resending issues a NEW link and permanently invalidates the previous one. The
 * copy says so plainly, so the operator is never surprised that a link they
 * already emailed out has stopped working.
 */
export function ResendConfirmation({
  entry,
  busy,
  onConfirm,
  onCancel,
}: {
  entry: AdminRosterEntry
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div
      role="alertdialog"
      aria-labelledby="resend-heading"
      className="mt-4 rounded-xl border border-violet-500/40 bg-violet-500/10 p-4"
    >
      <p id="resend-heading" className="text-sm font-semibold text-violet-100">
        Send a new invitation link to {entry.email}?
      </p>
      <p className="mt-1 text-xs text-violet-200/90">
        A new one-time link will be generated and emailed. The previous link stops
        working immediately &mdash; it is not reactivated by sending this one.
      </p>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          disabled={busy || entry.invitation_id === null}
          onClick={onConfirm}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
        >
          {busy ? 'Sending...' : 'Send new link'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          Keep current link
        </button>
      </div>
    </div>
  )
}

/**
 * Explicit revocation confirmation.
 *
 * The copy states exactly what will and will not happen, so the operator can
 * never over- or under-promise: only this institution's admin role is removed,
 * the account and any other role are preserved, and the action is audited.
 */
export function RevokeConfirmation({
  entry,
  busy,
  onConfirm,
  onCancel,
}: {
  entry: AdminRosterEntry
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div
      role="alertdialog"
      aria-labelledby="revoke-heading"
      className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4"
    >
      <p id="revoke-heading" className="text-sm font-semibold text-rose-100">
        Revoke University Admin access for {entry.email}?
      </p>
      <p className="mt-1 text-xs text-rose-200/90">
        This removes only this institution&apos;s admin role. The account itself and any
        other role it holds are preserved, and the action is recorded in the platform
        audit.
      </p>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          disabled={busy || entry.user_id === null}
          onClick={onConfirm}
          className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-300 disabled:opacity-50"
        >
          {busy ? 'Revoking...' : 'Revoke admin'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          Keep admin
        </button>
      </div>
    </div>
  )
}

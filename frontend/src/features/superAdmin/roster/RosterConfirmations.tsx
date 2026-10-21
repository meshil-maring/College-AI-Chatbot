import type { AdminRosterEntry } from '../../../types/platform.ts'

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
        A new one-time link will be generated and emailed. The previous link stops working immediately &mdash; it is not
        reactivated by sending this one.
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
        This removes only this institution&apos;s admin role. The account itself and any other role it holds are
        preserved, and the action is recorded in the platform audit.
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

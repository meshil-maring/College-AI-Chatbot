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
      className="mt-4 rounded-xl border border-accent bg-raised p-4"
    >
      <p id="resend-heading" className="text-sm font-semibold text-accent">
        Send a new invitation link to {entry.email}?
      </p>
      <p className="mt-1 text-xs text-accent">
        A new one-time link will be generated and emailed. The previous link stops working immediately &mdash; it is not
        reactivated by sending this one.
      </p>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          disabled={busy || entry.invitation_id === null}
          onClick={onConfirm}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
        >
          {busy ? 'Sending...' : 'Send new link'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
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
      className="mt-4 rounded-xl border border-danger bg-danger-bg p-4"
    >
      <p id="revoke-heading" className="text-sm font-semibold text-danger">
        Revoke University Admin access for {entry.email}?
      </p>
      <p className="mt-1 text-xs text-danger">
        This removes only this institution&apos;s admin role. The account itself and any other role it holds are
        preserved, and the action is recorded in the platform audit.
      </p>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          disabled={busy || entry.user_id === null}
          onClick={onConfirm}
          className="rounded-lg bg-danger-bg px-4 py-2 text-sm font-semibold text-content hover:bg-danger-bg focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
        >
          {busy ? 'Revoking...' : 'Revoke admin'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Keep admin
        </button>
      </div>
    </div>
  )
}

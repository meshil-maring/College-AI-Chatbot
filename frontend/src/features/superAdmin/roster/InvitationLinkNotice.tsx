import type { AdminInvitationCreated, AdminInvitationResend } from '../../../types/platform.ts'
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
    <div className="mt-4 rounded-xl border border-accent bg-raised p-4">
      <p className="text-sm font-semibold text-accent">Invitation link for {created.invitation.email}</p>
      <p className="mt-1 text-xs text-accent">
        This link is shown only once and expires in {created.expires_in_hours} hours. Copy it now — it cannot be
        retrieved again.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <code
          data-testid="invitation-link"
          className="max-w-full break-all rounded-lg border border-line bg-canvas px-3 py-2 text-xs text-muted"
        >
          {link}
        </code>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard?.writeText(link).then(() => setCopied(true))
          }}
          className="rounded-lg border border-accent px-3 py-2 text-xs font-medium text-accent hover:bg-raised focus:outline-none focus:ring-2 focus:ring-accent"
        >
          {copied ? 'Copied' : 'Copy link'}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-lg border border-control px-3 py-2 text-xs font-medium text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Done
        </button>
      </div>
    </div>
  )
}

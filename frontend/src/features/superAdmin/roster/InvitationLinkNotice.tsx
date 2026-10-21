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
    <div className="mt-4 rounded-xl border border-violet-500/40 bg-violet-500/10 p-4">
      <p className="text-sm font-semibold text-violet-100">Invitation link for {created.invitation.email}</p>
      <p className="mt-1 text-xs text-violet-200">
        This link is shown only once and expires in {created.expires_in_hours} hours. Copy it now — it cannot be
        retrieved again.
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

import { cancelInvitation, resendInvitation, revokeInstitutionAdmin } from '../../services/platform/platformInstitutionsApi.ts'
import { InvitationLinkNotice, ResendConfirmation, RevokeConfirmation, RosterTable } from './AdminRosterViews.tsx'
/**
 * Phase 7.14 University Admin roster: invite, cancel and revoke.
 *
 * This component holds NO authority of its own. It renders only after
 * `SuperAdminShell` received an allow response from `GET /platform/me`, and the
 * backend independently enforces `require_super_admin` on every call below.
 * Hiding or disabling a button is a UX affordance, never a security control.
 *
 * The invitation link is shown to the operator exactly once, immediately after
 * creation, with a controlled copy action. It is never persisted to storage and
 * never logged. Losing it means cancelling and reissuing the invitation.
 */

import { inputClass, labelClass, useAdminRoster } from './roster/useAdminRoster.ts'
export default function AdminRosterPanel(props: Parameters<typeof useAdminRoster>[0]) {
  const model = useAdminRoster(props)
  const {
    institutionId,
    institutionCode,
    token,
    roster,
    loading,
    busy,
    error,
    setError,
    notice,
    setNotice,
    showInvite,
    setShowInvite,
    email,
    setEmail,
    created,
    setCreated,
    resent,
    setResent,
    copied,
    setCopied,
    confirmRevoke,
    setConfirmRevoke,
    confirmResend,
    setConfirmResend,
    run,
    invite,
  } = model

  return (
    <section aria-labelledby="admin-roster-heading" className="rounded-2xl border border-slate-700 bg-slate-900 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id="admin-roster-heading" className="font-semibold text-white">
          University Admins
        </h3>
        <button
          type="button"
          onClick={() => {
            setShowInvite((open) => !open)
            setError(null)
            setNotice(null)
          }}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300"
        >
          + Invite Admin
        </button>
      </div>

      {error !== null ? (
        <p
          role="alert"
          className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
        >
          {error}
        </p>
      ) : null}
      {notice !== null ? (
        <p
          role="status"
          className="mt-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200"
        >
          {notice}
        </p>
      ) : null}

      {created !== null ? (
        <InvitationLinkNotice
          created={created}
          copied={copied}
          setCopied={setCopied}
          onDone={() => {
            setCreated(null)
            setCopied(false)
          }}
        />
      ) : null}

      {resent !== null ? (
        <InvitationLinkNotice
          created={resent}
          copied={copied}
          setCopied={setCopied}
          onDone={() => {
            setResent(null)
          }}
        />
      ) : null}

      {showInvite ? (
        <form
          className="mt-4 rounded-xl border border-slate-700 bg-slate-950 p-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (email.trim() === '' || busy !== null) return
            void invite()
          }}
        >
          <label className={labelClass} htmlFor="invite-email">
            Email
          </label>
          <input
            id="invite-email"
            type="email"
            className={inputClass}
            value={email}
            onChange={(event) => {
              setEmail(event.target.value)
            }}
            placeholder="dean@university.example"
            required
          />
          <p className="mt-2 text-xs text-slate-500">
            Invitation expires in 24 hours. No password is set here — the invited person creates their own when they
            open the link.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <button
              type="submit"
              disabled={busy !== null || email.trim() === ''}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
            >
              {busy === 'invite' ? 'Creating invitation...' : 'Create Invitation'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowInvite(false)
              }}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}
      {loading ? (
        <p role="status" className="mt-4 text-sm text-slate-400">
          Loading admin roster...
        </p>
      ) : roster === null ? null : (
        <RosterTable
          roster={roster}
          institutionCode={institutionCode}
          busy={busy}
          onCancel={(entry) =>
            void run('cancel', async () => {
              const result = await cancelInvitation(token, institutionId, entry.invitation_id as string)
              return result.already_applied ? `The invitation for ${entry.email} was already closed.` : result.message
            })
          }
          onResend={(entry) => {
            setConfirmResend(entry)
            setError(null)
            setNotice(null)
          }}
          onRevoke={(entry) => {
            setConfirmRevoke(entry)
            setError(null)
            setNotice(null)
          }}
        />
      )}

      {confirmResend !== null ? (
        <ResendConfirmation
          entry={confirmResend}
          busy={busy === 'resend'}
          onCancel={() => {
            setConfirmResend(null)
          }}
          onConfirm={() => {
            const target = confirmResend
            setConfirmResend(null)
            void run('resend', async () => {
              const result = await resendInvitation(token, institutionId, target.invitation_id as string)
              // The new one-time link is surfaced here, exactly as on creation,
              // so the operator has a fallback if the email does not arrive. It
              // is held in component state only — never persisted or logged.
              setResent(
                result.email_delivery.provider === 'local' || result.email_delivery.provider === 'test' ? result : null,
              )
              setCopied(false)
              if (result.email_delivery.status === 'pending') return 'Invitation email queued'
              return result.email_delivery.status === 'sent'
                ? result.message
                : 'Invitation could not be delivered. Try again later.'
            })
          }}
        />
      ) : null}

      {confirmRevoke !== null ? (
        <RevokeConfirmation
          entry={confirmRevoke}
          busy={busy === 'revoke'}
          onCancel={() => {
            setConfirmRevoke(null)
          }}
          onConfirm={() => {
            const target = confirmRevoke
            setConfirmRevoke(null)
            void run('revoke', async () => {
              const result = await revokeInstitutionAdmin(token, institutionId, target.user_id as string)
              return result.revoked
                ? `${target.email} is no longer a University Admin of this institution.`
                : result.message
            })
          }}
        />
      ) : null}
    </section>
  )
}

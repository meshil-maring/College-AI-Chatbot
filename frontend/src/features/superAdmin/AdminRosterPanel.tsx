import { useCallback, useEffect, useState } from 'react'
import {
  PlatformInstitutionError,
  cancelInvitation,
  createInvitation,
  getAdminRoster,
  resendInvitation,
  revokeInstitutionAdmin,
} from '../../services/platformInstitutionsApi.ts'
import type {
  AdminInvitationCreated,
  AdminInvitationResend,
  AdminRoster,
  AdminRosterEntry,
} from '../../types/platform.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  InvitationLinkNotice,
  ResendConfirmation,
  RevokeConfirmation,
  RosterTable,
} from './AdminRosterViews.tsx'

const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'
const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

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
export default function AdminRosterPanel({
  institutionId,
  institutionCode,
  onChanged,
}: {
  institutionId: string
  institutionCode: string
  /** Let the parent refresh its institution detail (admin_count) afterwards. */
  onChanged?: () => void
}) {
  const { accessToken } = useAuth()
  const token = accessToken ?? ''

  const [roster, setRoster] = useState<AdminRoster | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'invite' | 'cancel' | 'resend' | 'revoke' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [showInvite, setShowInvite] = useState(false)
  const [email, setEmail] = useState('')
  const [created, setCreated] = useState<AdminInvitationCreated | null>(null)
  // Phase 7.15: the same one-time-link reveal, reused after a resend so an
  // operator who loses the emailed message still has a fallback link.
  const [resent, setResent] = useState<AdminInvitationResend | null>(null)
  const [copied, setCopied] = useState(false)
  const [confirmRevoke, setConfirmRevoke] = useState<AdminRosterEntry | null>(null)
  const [confirmResend, setConfirmResend] = useState<AdminRosterEntry | null>(null)

  const refresh = useCallback(async (): Promise<void> => {
    if (token === '') return
    setLoading(true)
    try {
      setRoster(await getAdminRoster(token, institutionId))
    } catch (err) {
      setError(
        err instanceof PlatformInstitutionError
          ? err.message
          : 'Could not load the admin roster. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }, [token, institutionId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const run = useCallback(
    async (
      action: 'invite' | 'cancel' | 'resend' | 'revoke',
      operation: () => Promise<string>,
    ): Promise<void> => {
      setBusy(action)
      setError(null)
      setNotice(null)
      try {
        setNotice(await operation())
        await refresh()
        onChanged?.()
      } catch (err) {
        setError(
          err instanceof PlatformInstitutionError
            ? err.message
            : 'Something went wrong. Please try again.',
        )
      } finally {
        setBusy(null)
      }
    },
    [refresh, onChanged],
  )

  const invite = (): Promise<void> =>
    run('invite', async () => {
      const result = await createInvitation(token, institutionId, { email: email.trim() })
      // Raw-link fallback is limited to responses from the explicit local/test
      // capture providers. A production provider response never renders it.
      setCreated(
        result.email_delivery?.provider === 'local' || result.email_delivery?.provider === 'test'
          ? result
          : null,
      )
      setCopied(false)
      setEmail('')
      setShowInvite(false)
      if (result.email_delivery?.status === 'pending') return 'Invitation email queued'
      return result.email_delivery?.status === 'sent'
        ? 'Invitation sent'
        : 'Invitation could not be delivered. Try again later.'
    })

  return (
    <section
      aria-labelledby="admin-roster-heading"
      className="rounded-2xl border border-slate-700 bg-slate-900 p-6"
    >
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
          onDone={() => { setCreated(null); setCopied(false) }}
        />
      ) : null}

      {resent !== null ? (
        <InvitationLinkNotice
          created={resent}
          copied={copied}
          setCopied={setCopied}
          onDone={() => { setResent(null) }}
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
            onChange={(event) => { setEmail(event.target.value) }}
            placeholder="dean@university.example"
            required
          />
          <p className="mt-2 text-xs text-slate-500">
            Invitation expires in 24 hours. No password is set here — the invited person
            creates their own when they open the link.
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
              onClick={() => { setShowInvite(false) }}
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
              const result = await cancelInvitation(
                token,
                institutionId,
                entry.invitation_id as string,
              )
              return result.already_applied
                ? `The invitation for ${entry.email} was already closed.`
                : result.message
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
          onCancel={() => { setConfirmResend(null) }}
          onConfirm={() => {
            const target = confirmResend
            setConfirmResend(null)
            void run('resend', async () => {
              const result = await resendInvitation(
                token,
                institutionId,
                target.invitation_id as string,
              )
              // The new one-time link is surfaced here, exactly as on creation,
              // so the operator has a fallback if the email does not arrive. It
              // is held in component state only — never persisted or logged.
              setResent(
                result.email_delivery.provider === 'local' || result.email_delivery.provider === 'test'
                  ? result
                  : null,
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
          onCancel={() => { setConfirmRevoke(null) }}
          onConfirm={() => {
            const target = confirmRevoke
            setConfirmRevoke(null)
            void run('revoke', async () => {
              const result = await revokeInstitutionAdmin(
                token,
                institutionId,
                target.user_id as string,
              )
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

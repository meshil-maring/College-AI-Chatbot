import { useCallback, useEffect, useState } from 'react'
import {
  AdminInvitationError,
  acceptInvitation,
  inspectInvitation,
} from '../../services/adminInvitationApi.ts'
import type { AdminInvitationPublicView } from '../../types/platform.ts'

type Phase =
  | { readonly kind: 'loading' }
  | { readonly kind: 'unusable'; readonly message: string }
  | { readonly kind: 'ready'; readonly invitation: AdminInvitationPublicView }
  | { readonly kind: 'submitting'; readonly invitation: AdminInvitationPublicView }
  | { readonly kind: 'accepted'; readonly institutionName: string; readonly message: string; readonly role: 'admin' | 'staff' | 'faculty' }

const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400'
const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

function formatExpiry(value: string | null): string {
  if (value === null) return 'an unknown time'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

/**
 * Phase 7.14 invitation acceptance route (`/admin-invite/{token}`).
 *
 * The token in the URL is treated strictly as an OPAQUE LOOKUP CREDENTIAL. No
 * institution, role or scope is ever read from the URL — the page shows only
 * what the server says this token is bound to, and the server resolves
 * `invitation -> institution -> role` itself. That is why the displayed
 * institution name can be trusted: it is the server's answer, not a guess built
 * from client-side input.
 *
 * Security posture of this page:
 * - Unauthenticated by design: the invited person has no account yet.
 * - The password entered here goes straight to the backend, which forwards it
 *   to Supabase Auth. It is never persisted, never logged and never returned.
 * - No session is created. On success the person signs in through the ordinary
 *   admin login page with the password they just chose.
 * - Terminal failures (expired / cancelled / already used) say so plainly and
 *   offer no retry, because retrying could never succeed.
 */
export default function AdminInvitationPage({ token }: { token: string }) {
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' })
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const inspect = useCallback(async (): Promise<void> => {
    setPhase({ kind: 'loading' })
    try {
      setPhase({ kind: 'ready', invitation: await inspectInvitation(token) })
    } catch (err) {
      setPhase({
        kind: 'unusable',
        message:
          err instanceof AdminInvitationError
            ? err.message
            : 'This invitation link could not be verified.',
      })
    }
  }, [token])

  useEffect(() => {
    void inspect()
  }, [inspect])

  const submit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    setLocalError(null)
    if (phase.kind !== 'ready') return
    if (password.length < 8) {
      setLocalError('Choose a password of at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setLocalError('The two passwords do not match.')
      return
    }
    const invitation = phase.invitation
    setPhase({ kind: 'submitting', invitation })
    try {
      const result = await acceptInvitation(token, {
        password,
        ...(firstName.trim() !== '' ? { first_name: firstName.trim() } : {}),
        ...(lastName.trim() !== '' ? { last_name: lastName.trim() } : {}),
      })
      // Clear the password from component state immediately on success.
      setPassword('')
      setConfirmPassword('')
      setPhase({
        kind: 'accepted',
        institutionName: result.institution_name,
        message: result.message,
        role: result.role,
      })
    } catch (err) {
      // A terminal failure can never succeed on retry, so stop offering the form.
      if (err instanceof AdminInvitationError && err.isTerminal) {
        setPhase({ kind: 'unusable', message: err.message })
        return
      }
      setPhase({ kind: 'ready', invitation })
      setLocalError(
        err instanceof AdminInvitationError
          ? err.message
          : 'We could not complete your account setup. Please try again.',
      )
    }
  }
return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <section className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">
          University Admin Invitation
        </p>

        {phase.kind === 'loading' ? (
          <p role="status" className="mt-4 text-sm text-slate-400">
            Verifying your invitation…
          </p>
        ) : null}

        {phase.kind === 'unusable' ? (
          <>
            <h1 className="mt-2 text-2xl font-bold text-white">This invitation cannot be used</h1>
            <p role="alert" className="mt-4 text-sm leading-6 text-slate-300">
              {phase.message}
            </p>
            <p className="mt-4 text-sm leading-6 text-slate-400">
              Ask your platform administrator to send a new invitation.
            </p>
            <a
              href="/login/admin"
              className="mt-6 inline-block rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-300"
            >
              Go to admin login
            </a>
          </>
        ) : null}

        {phase.kind === 'accepted' ? (
          <>
            <h1 className="mt-2 text-2xl font-bold text-white">Your account is ready</h1>
            <p role="status" className="mt-4 text-sm leading-6 text-emerald-200">
              {phase.message}
            </p>
            <p className="mt-3 text-sm text-slate-400">
              You were added as {phase.role === 'admin' ? 'a University Admin' : phase.role} of {phase.institutionName}.
            </p>
            <a
              href={`/login/${phase.role}`}
              className="mt-6 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300"
            >
              Continue to {phase.role === 'admin' ? 'admin' : phase.role} login
            </a>
          </>
        ) : null}

        {phase.kind === 'ready' || phase.kind === 'submitting' ? (
          <>
            <h1 className="mt-2 text-2xl font-bold text-white">
              Join {phase.invitation.institution_name}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              This invitation is for{' '}
              <strong className="text-slate-200">{phase.invitation.email}</strong>. Create a
              password to finish setting up your {phase.invitation.role === 'admin' || phase.invitation.role === undefined ? 'University Admin' : phase.invitation.role} account.
            </p>
            {/* Phase 7.15: the email is INFORMATIONAL. It is rendered from the
                server's answer, is not an input, and cannot be edited — the
                account this invitation creates is bound to this address no
                matter what is typed below. The verification state shown here is
                also the server's, never a local flag. */}
            <p
              data-testid="invite-email-binding"
              className="mt-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300"
            >
              Your account will be created for{' '}
              <strong className="text-slate-100">{phase.invitation.email}</strong>.
              This address cannot be changed during setup.
            </p>
            <p
              data-testid="invite-verification-state"
              className="mt-2 text-xs text-slate-500"
            >
              {phase.invitation.email_verified
                ? 'Email verified'
                : 'Invitation valid — email will be verified when you complete setup.'}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Expires: {formatExpiry(phase.invitation.expires_at)}
            </p>

            {localError !== null ? (
              <p
                role="alert"
                className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
              >
                {localError}
              </p>
            ) : null}

            <form className="mt-6 space-y-4" onSubmit={(event) => { void submit(event) }}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="invite-first-name">
                    First name (optional)
                  </label>
                  <input
                    id="invite-first-name"
                    className={inputClass}
                    value={firstName}
                    onChange={(event) => { setFirstName(event.target.value) }}
                    autoComplete="given-name"
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor="invite-last-name">
                    Last name (optional)
                  </label>
                  <input
                    id="invite-last-name"
                    className={inputClass}
                    value={lastName}
                    onChange={(event) => { setLastName(event.target.value) }}
                    autoComplete="family-name"
                  />
                </div>
              </div>
              <div>
                <label className={labelClass} htmlFor="invite-password">
                  Password
                </label>
                <input
                  id="invite-password"
                  type="password"
                  className={inputClass}
                  value={password}
                  onChange={(event) => { setPassword(event.target.value) }}
                  autoComplete="new-password"
                  required
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="invite-confirm-password">
                  Confirm password
                </label>
                <input
                  id="invite-confirm-password"
                  type="password"
                  className={inputClass}
                  value={confirmPassword}
                  onChange={(event) => { setConfirmPassword(event.target.value) }}
                  autoComplete="new-password"
                  required
                />
              </div>
              <p className="text-xs text-slate-500">
                Your password is sent only to the College AI authentication service and is never
                stored or displayed by this page.
              </p>
              <button
                type="submit"
                disabled={phase.kind === 'submitting'}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
              >
                {phase.kind === 'submitting' ? 'Setting up your account…' : 'Create my account'}
              </button>
            </form>
          </>
        ) : null}
      </section>
    </main>
  )
}

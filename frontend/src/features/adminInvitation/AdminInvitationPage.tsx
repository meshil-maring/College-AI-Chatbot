import { InvitationAcceptanceForm } from './InvitationAcceptanceForm.tsx'
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

import { formatExpiry, useInvitationAcceptance } from './useInvitationAcceptance.ts'
export type { Phase } from './useInvitationAcceptance.ts'

export default function AdminInvitationPage(props: Parameters<typeof useInvitationAcceptance>[0]) {
  const model = useInvitationAcceptance(props)
  const { phase, recoveryMode, membershipMode, localError } = model

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
      <section className="w-full max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">University Admin Invitation</p>

        {phase.kind === 'loading' ? (
          <p role="status" className="mt-4 text-sm text-muted">
            Verifying your invitation…
          </p>
        ) : null}

        {phase.kind === 'unusable' ? (
          <>
            <h1 className="mt-2 font-bold text-content text-page">This invitation cannot be used</h1>
            <p role="alert" className="mt-4 text-sm leading-6 text-muted">
              {phase.message}
            </p>
            <p className="mt-4 text-sm leading-6 text-muted">
              Contact your administrator for help with this invitation.
            </p>
            <a
              href="/login/admin"
              className="mt-6 inline-block rounded-lg bg-raised px-4 py-2 text-sm font-semibold text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Go to admin login
            </a>
          </>
        ) : null}

        {phase.kind === 'accepted' ? (
          <>
            <h1 className="mt-2 font-bold text-content text-page">Your account is ready</h1>
            <p role="status" className="mt-4 text-sm leading-6 text-success">
              {phase.message}
            </p>
            <p className="mt-3 text-sm text-muted">
              You were added as {phase.role === 'admin' ? 'a University Admin' : phase.role} of {phase.institutionName}.
            </p>
            <a
              href={`/login/${phase.role}`}
              className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Continue to {phase.role === 'admin' ? 'admin' : phase.role} login
            </a>
          </>
        ) : null}

        {phase.kind === 'ready' || phase.kind === 'submitting' ? (
          <>
            <h1 className="mt-2 font-bold text-content text-page">Join {phase.invitation.institution_name}</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              This invitation is for <strong className="text-content">{phase.invitation.email}</strong>.
              {recoveryMode
                ? ' Finish confirming the account you already created.'
                : membershipMode
                  ? ' Accept membership using your signed-in account.'
                  : ' Create a password to finish setting up your account.'}
            </p>
            {/* Phase 7.15: the email is INFORMATIONAL. It is rendered from the
                server's answer, is not an input, and cannot be edited — the
                account this invitation creates is bound to this address no
                matter what is typed below. The verification state shown here is
                also the server's, never a local flag. */}
            <p
              data-testid="invite-email-binding"
              className="mt-2 rounded-lg border border-line bg-canvas px-3 py-2 text-xs text-muted"
            >
              This membership is bound to <strong className="text-content">{phase.invitation.email}</strong>. This
              address cannot be changed during setup.
            </p>
            <p data-testid="invite-verification-state" className="mt-2 text-xs text-muted">
              {phase.invitation.email_verified
                ? 'Email verified'
                : 'Invitation valid — email will be verified when you complete setup.'}
            </p>
            <p className="mt-2 text-xs text-muted">Expires: {formatExpiry(phase.invitation.expires_at)}</p>

            {localError !== null ? (
              <p
                role="alert"
                className="mt-4 rounded-xl border border-danger bg-danger-bg px-4 py-3 text-sm text-danger"
              >
                {localError}
              </p>
            ) : null}

            <InvitationAcceptanceForm model={model} />
          </>
        ) : null}
      </section>
    </main>
  )
}

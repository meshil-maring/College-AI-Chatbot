import type { AdminInvitationPageModel } from './useInvitationAcceptance.ts'
import { inputClass, labelClass } from './useInvitationAcceptance.ts'
export function InvitationAcceptanceForm({ model }: { model: AdminInvitationPageModel }) {
  const {
    auth,
    setExistingAccount,
    phase,
    recoveryMode,
    membershipMode,
    password,
    setPassword,
    confirmPassword,
    setConfirmPassword,
    firstName,
    setFirstName,
    lastName,
    setLastName,
    submit,
  } = model
  if (phase.kind !== 'ready' && phase.kind !== 'submitting') return null
  return (
    <form
      className="mt-6 space-y-4"
      onSubmit={(event) => {
        void submit(event)
      }}
    >
      {phase.invitation.status === 'accepted' ? (
        <p role="status">
          This invitation has already been accepted.{' '}
          {recoveryMode ? 'Retry confirmation without signing in.' : 'Sign in to recover your acceptance result.'}
        </p>
      ) : null}
      {recoveryMode ? (
        <button type="submit" disabled={phase.kind === 'submitting'}>
          Retry account recovery
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={() => {
              setExistingAccount(true)
              setPassword('')
              setConfirmPassword('')
            }}
          >
            I already have an account
          </button>
          {membershipMode ? (
            <>
              <p>Your existing credentials will be preserved.</p>
              {auth.status !== 'authenticated' ? (
                <a href={`/login/${phase.invitation.role ?? 'admin'}`}>Sign in, then return to this invitation</a>
              ) : null}
              <button type="submit" disabled={phase.kind === 'submitting' || auth.status !== 'authenticated'}>
                Accept membership
              </button>
            </>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="invite-first-name">
                    First name (optional)
                  </label>
                  <input
                    id="invite-first-name"
                    className={inputClass}
                    value={firstName}
                    onChange={(event) => {
                      setFirstName(event.target.value)
                    }}
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
                    onChange={(event) => {
                      setLastName(event.target.value)
                    }}
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
                  onChange={(event) => {
                    setPassword(event.target.value)
                  }}
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
                  onChange={(event) => {
                    setConfirmPassword(event.target.value)
                  }}
                  autoComplete="new-password"
                  required
                />
              </div>
              <p className="text-xs text-slate-500">
                Your password is sent only to the College AI authentication service and is never stored or displayed by
                this page.
              </p>
              <button
                type="submit"
                disabled={phase.kind === 'submitting'}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
              >
                {phase.kind === 'submitting' ? 'Setting up your account…' : 'Create my account'}
              </button>
            </>
          )}
        </>
      )}
    </form>
  )
}

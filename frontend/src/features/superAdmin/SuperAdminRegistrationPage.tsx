import { useEffect, useState } from 'react'
import {
  SuperAdminInvitationError,
  inspectSuperAdminInvitation,
  registerSuperAdmin,
  type SuperAdminInvitePublicView,
} from '../../services/superAdminInvitationApi.ts'

type Phase =
  | { readonly kind: 'loading' }
  | { readonly kind: 'unusable'; readonly message: string }
  | { readonly kind: 'ready'; readonly invitation: SuperAdminInvitePublicView }
  | { readonly kind: 'submitting'; readonly invitation: SuperAdminInvitePublicView }
  | { readonly kind: 'done'; readonly message: string }

const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'
const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

/**
 * Invitation-only Super Admin registration (`/super-admin-invite/{token}`).
 * The email, role and scope come from the server-side invitation; the page
 * only collects a name and the person's own password.
 */
export default function SuperAdminRegistrationPage({ token }: { token: string }) {
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' })
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    inspectSuperAdminInvitation(token).then(
      (invitation) => { if (!cancelled) setPhase({ kind: 'ready', invitation }) },
      (err: unknown) => {
        if (cancelled) return
        setPhase({
          kind: 'unusable',
          message:
            err instanceof SuperAdminInvitationError
              ? err.message
              : 'This invitation link could not be verified.',
        })
      },
    )
    return () => { cancelled = true }
  }, [token])

  const submit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    setError(null)
    if (phase.kind !== 'ready') return
    if (firstName.trim() === '' || lastName.trim() === '') {
      setError('Enter your first and last name.')
      return
    }
    if (password.length < 8) {
      setError('Choose a password of at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('The two passwords do not match.')
      return
    }
    const invitation = phase.invitation
    setPhase({ kind: 'submitting', invitation })
    try {
      const result = await registerSuperAdmin(token, {
        password,
        confirm_password: confirmPassword,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      })
      setPassword('')
      setConfirmPassword('')
      setPhase({ kind: 'done', message: result.message })
    } catch (err) {
      if (err instanceof SuperAdminInvitationError && err.isTerminal) {
        setPhase({ kind: 'unusable', message: err.message })
        return
      }
      setPhase({ kind: 'ready', invitation })
      setError(
        err instanceof SuperAdminInvitationError
          ? err.message
          : 'We could not complete registration. Please try again.',
      )
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <section className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
          Super Admin Invitation
        </p>
        <h1 className="mt-2 text-2xl font-bold">Create your Super Admin account</h1>

        {phase.kind === 'loading' ? <p className="mt-6 text-sm text-slate-400">Verifying invitation…</p> : null}

        {phase.kind === 'unusable' ? (
          <p role="alert" className="mt-6 text-sm text-amber-300">{phase.message}</p>
        ) : null}

        {phase.kind === 'done' ? (
          <div className="mt-6">
            <p role="status" className="text-sm text-emerald-300">{phase.message}</p>
            <a href="/login/admin" className="mt-4 inline-block text-sm text-violet-300 underline">Go to sign in</a>
          </div>
        ) : null}

        {phase.kind === 'ready' || phase.kind === 'submitting' ? (
          <form onSubmit={(e) => { void submit(e) }} className="mt-6 space-y-4" noValidate>
            <p className="text-sm text-slate-300">
              Registering <strong>{phase.invitation.email}</strong>
            </p>
            <div>
              <label htmlFor="sa-first" className={labelClass}>First name</label>
              <input id="sa-first" className={inputClass} value={firstName} maxLength={200} onChange={(e) => { setFirstName(e.target.value) }} autoComplete="given-name" />
            </div>
            <div>
              <label htmlFor="sa-last" className={labelClass}>Last name</label>
              <input id="sa-last" className={inputClass} value={lastName} maxLength={200} onChange={(e) => { setLastName(e.target.value) }} autoComplete="family-name" />
            </div>
            <div>
              <label htmlFor="sa-password" className={labelClass}>Password</label>
              <input id="sa-password" type="password" className={inputClass} value={password} maxLength={200} onChange={(e) => { setPassword(e.target.value) }} autoComplete="new-password" />
            </div>
            <div>
              <label htmlFor="sa-confirm" className={labelClass}>Confirm password</label>
              <input id="sa-confirm" type="password" className={inputClass} value={confirmPassword} maxLength={200} onChange={(e) => { setConfirmPassword(e.target.value) }} autoComplete="new-password" />
            </div>
            {error !== null ? <p role="alert" className="text-sm text-red-400">{error}</p> : null}
            <button type="submit" disabled={phase.kind === 'submitting'} className="w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-60">
              {phase.kind === 'submitting' ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        ) : null}
      </section>
    </main>
  )
}

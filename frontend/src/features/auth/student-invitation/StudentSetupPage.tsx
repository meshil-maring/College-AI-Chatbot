import { useEffect, useState, type FormEvent } from 'react'
import {
  completeStudentSetup,
  inspectStudentSetup,
  type StudentInvitationDetails,
} from '../../../services/registration/studentOnboarding.ts'

type State = 'loading' | 'ready' | 'submitting' | 'complete' | 'unavailable'

export default function StudentSetupPage() {
  const [token] = useState(() => window.location.hash.slice(1))
  const [details, setDetails] = useState<StudentInvitationDetails>()
  const [state, setState] = useState<State>('loading')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    if (!token) {
      setError('This setup link is incomplete. Ask your administrator to send a new one.')
      setState('unavailable')
      return () => { active = false }
    }
    void inspectStudentSetup(token).then((response) => {
      if (!active) return
      setDetails(response)
      setState(response.status === 'accepted' ? 'complete' : 'ready')
      if (response.status === 'accepted') setMessage('Your student account is already ready. Sign in to continue.')
    }).catch((reason: unknown) => {
      if (!active) return
      setError(reason instanceof Error ? reason.message : 'This setup link is invalid or expired.')
      setState('unavailable')
    })
    return () => { active = false }
  }, [token])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmation) {
      setError('The passwords do not match.')
      return
    }
    if (!token) return
    setState('submitting')
    setError('')
    try {
      const result = await completeStudentSetup(token, password)
      setMessage(result.message)
      setState('complete')
      window.history.replaceState(window.history.state, '', window.location.pathname)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Password setup could not be completed.')
      setState('ready')
      try {
        const refreshed = await inspectStudentSetup(token)
        setDetails(refreshed)
      } catch {
        setState('unavailable')
      }
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
      <section className="w-full max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Student Account Setup</p>
        {state === 'loading' && <p role="status" className="mt-4 text-sm text-muted">Checking your secure setup link…</p>}
        {state === 'unavailable' && (
          <>
            <h1 className="mt-3 font-bold text-content text-page">This setup link cannot be used</h1>
            <p role="alert" className="mt-4 text-sm leading-6 text-muted">{error}</p>
            <p className="mt-3 text-sm text-muted">Contact your institution administrator for help with this invitation.</p>
            <a href="/login/student" className="mt-6 inline-block rounded-lg bg-raised px-4 py-2 text-sm font-semibold text-content">
              Go to student login
            </a>
          </>
        )}
        {details && (state === 'ready' || state === 'submitting' || state === 'complete') && (
          <>
            <h1 className="mt-3 font-bold text-content text-page">
              {state === 'complete' ? 'Your account is ready' : `Welcome, ${details.student_name}`}
            </h1>
            <p className="mt-3 text-sm leading-6 text-muted">
              {details.institution_name} · {details.batch_code} ({details.batch_name}) · {details.section_name}
            </p>
            <p className="mt-2 text-sm text-muted">Account email: <strong>{details.email}</strong></p>
            {state === 'complete' ? (
              <>
                <p role="status" className="mt-4 text-sm leading-6 text-success">{message}</p>
                <a href="/login/student" className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink">
                  Continue to student login
                </a>
              </>
            ) : !details.section_active ? (
              <p role="alert" className="mt-4 text-sm leading-6 text-danger">
                This section is no longer active. Ask your administrator to assign an active section, then request a new setup link.
              </p>
            ) : (
              <>
                <p className="mt-3 text-sm text-muted">
                  This link expires at {new Date(details.expires_at).toLocaleString()} and can be used once.
                </p>
                {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
                <form className="mt-5 grid gap-4" onSubmit={(event) => void submit(event)}>
                  <label className="grid gap-1 text-sm font-semibold">
                    Create password
                    <input type="password" autoComplete="new-password" minLength={8} maxLength={128}
                      required value={password} disabled={state === 'submitting'}
                      onChange={(event) => setPassword(event.target.value)} />
                  </label>
                  <label className="grid gap-1 text-sm font-semibold">
                    Confirm password
                    <input type="password" autoComplete="new-password" minLength={8} maxLength={128}
                      required value={confirmation} disabled={state === 'submitting'}
                      onChange={(event) => setConfirmation(event.target.value)} />
                  </label>
                  <button type="submit" disabled={state === 'submitting'}
                    className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink">
                    {state === 'submitting' ? 'Setting up your account…' : 'Verify and set password'}
                  </button>
                </form>
              </>
            )}
          </>
        )}
      </section>
    </main>
  )
}

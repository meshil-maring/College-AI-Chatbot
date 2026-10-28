import { useState } from 'react'
import { useAuth } from '../features/auth/session/AuthProvider.tsx'

export function StudentAccountSwitch({ registering }: { registering: boolean }) {
  const { role, logout } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const account =
    role === 'admin'
      ? 'an administrator'
      : role === 'super_admin'
        ? 'a platform administrator'
        : role === 'faculty'
          ? 'a faculty member'
          : role === 'staff'
            ? 'a staff member'
            : role === 'student'
              ? 'a student'
              : 'another account'

  async function continueAsStudent() {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await logout()
    } catch {
      setError('Could not sign out. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4 py-16 text-content">
      <section className="w-full max-w-md rounded-xl border border-line bg-surface p-8 shadow-none" aria-busy={busy}>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-success">Student access</p>
        <h1 className="mt-3 font-bold text-page">{registering ? 'Student registration' : 'Student sign in'}</h1>
        <p className="mt-4 text-sm leading-6 text-muted">
          You are currently signed in as {account}. Sign out to continue with this student{' '}
          {registering ? 'registration' : 'sign-in'}.
        </p>
        <p className="mt-3 text-sm leading-6 text-muted">This also signs out other CollegeAI tabs in this browser.</p>
        {error && (
          <p role="alert" className="mt-4 text-sm text-danger">
            {error}
          </p>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={() => void continueAsStudent()}
          className="mt-6 w-full rounded-lg bg-accent px-4 py-3 font-semibold text-ink hover:bg-accent-hover disabled:opacity-50"
        >
          {busy ? 'Signing out…' : 'Sign out and continue'}
        </button>
        <a href="/" className="mt-4 block text-center text-sm text-muted underline hover:text-content">
          Continue with current account
        </a>
      </section>
    </main>
  )
}

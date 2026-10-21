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
    <main className="flex min-h-screen items-center justify-center bg-slate-900 px-4 py-16 text-slate-100">
      <section
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl"
        aria-busy={busy}
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-400">Student access</p>
        <h1 className="mt-3 text-2xl font-bold">{registering ? 'Student registration' : 'Student sign in'}</h1>
        <p className="mt-4 text-sm leading-6 text-slate-300">
          You are currently signed in as {account}. Sign out to continue with this student{' '}
          {registering ? 'registration' : 'sign-in'}.
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          This also signs out other CollegeAI tabs in this browser.
        </p>
        {error && (
          <p role="alert" className="mt-4 text-sm text-red-300">
            {error}
          </p>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={() => void continueAsStudent()}
          className="mt-6 w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? 'Signing out…' : 'Sign out and continue'}
        </button>
        <a href="/" className="mt-4 block text-center text-sm text-slate-300 underline hover:text-white">
          Continue with current account
        </a>
      </section>
    </main>
  )
}

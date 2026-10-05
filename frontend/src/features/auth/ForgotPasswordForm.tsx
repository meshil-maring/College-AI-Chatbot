import { useState } from 'react'
import { AuthError, requestPasswordRecovery } from '../../services/auth.ts'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const RECOVERY_SUBMITTED_MESSAGE =
  'If an account exists, password recovery instructions have been sent.'

export interface ForgotPasswordFormProps {
  onBackToLogin: () => void
}

export default function ForgotPasswordForm({ onBackToLogin }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (busy) return
    const address = email.trim()
    if (!EMAIL_PATTERN.test(address)) {
      setError(address ? 'Please enter a valid email address.' : 'Please enter your email address.')
      return
    }

    setError(null)
    setBusy(true)
    try {
      await requestPasswordRecovery(address)
      setSubmitted(true)
      setEmail('')
    } catch (requestError) {
      setError(
        requestError instanceof AuthError
          ? requestError.message
          : 'Password recovery could not be requested. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white tracking-tight">Reset Password</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Enter your account email and we will send recovery instructions if an account matches.
          </p>
          {error !== null && (
            <div role="alert" className="mt-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
              {error}
            </div>
          )}
          {submitted && (
            <div role="status" className="mt-4 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
              {RECOVERY_SUBMITTED_MESSAGE}
            </div>
          )}
          <form
            className="mt-6 flex flex-col gap-5"
            noValidate
            aria-busy={busy}
            onSubmit={(event) => void handleSubmit(event)}
          >
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Email
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={busy || submitted}
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={busy || submitted}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Sending instructions…' : 'Send recovery instructions'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={onBackToLogin}
              className="text-sm text-slate-400 hover:text-slate-200 underline"
            >
              Back to Login
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

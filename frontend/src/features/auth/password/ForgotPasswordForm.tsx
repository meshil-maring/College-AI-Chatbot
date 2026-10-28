import { useState } from 'react'
import { AuthError, requestPasswordRecovery } from '../../../services/auth/auth.ts'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const RECOVERY_SUBMITTED_MESSAGE = 'If an account exists, password recovery instructions have been sent.'

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
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-xl border border-line bg-surface p-8 shadow-none">
          <h1 className="font-bold text-content tracking-tight text-page">Reset Password</h1>
          <p className="mt-2 text-sm text-muted leading-relaxed">
            Enter your account email and we will send recovery instructions if an account matches.
          </p>
          {error !== null && (
            <div
              role="alert"
              className="mt-4 rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger"
            >
              {error}
            </div>
          )}
          {submitted && (
            <div
              role="status"
              className="mt-4 rounded-lg border border-success bg-success-bg px-4 py-2 text-sm text-success"
            >
              {RECOVERY_SUBMITTED_MESSAGE}
            </div>
          )}
          <form
            className="mt-6 flex flex-col gap-5"
            noValidate
            aria-busy={busy}
            onSubmit={(event) => void handleSubmit(event)}
          >
            <label className="flex flex-col gap-1 text-sm text-muted">
              Email
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={busy || submitted}
                className="rounded-lg border border-control bg-surface px-3 py-2 text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={busy || submitted}
              className="rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Sending instructions…' : 'Send recovery instructions'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={onBackToLogin}
              className="text-sm text-muted hover:text-content underline"
            >
              Back to Login
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

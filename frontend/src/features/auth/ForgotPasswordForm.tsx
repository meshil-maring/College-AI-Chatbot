/**
 * DEVELOPMENT / TESTING ONLY — password reset without OTP/email verification.
 *
 * This component is only rendered when the backend reports
 * `DEV_TEST_MODE=true` (see `services/devAuth.ts` -> fetchDevAuthStatus).
 * It exists purely as a local development/testing convenience and must NOT
 * be part of the final demo. It reuses the existing Supabase-authenticated
 * backend flow — no password is stored locally, logged, or placed in a URL.
 */

import { useState } from 'react'
import { DevAuthError, devAuthErrorMessage, devForgotPassword } from '../../services/devAuth.ts'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export interface ForgotPasswordFormProps {
  onBackToLogin: () => void
}

export default function ForgotPasswordForm({ onBackToLogin }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  function validate(): string | null {
    if (!EMAIL_PATTERN.test(email)) {
      return 'Please enter a valid email address.'
    }
    if (newPassword.length < 6) {
      return 'Password must be at least 6 characters.'
    }
    if (newPassword !== confirmPassword) {
      return 'Passwords do not match.'
    }
    return null
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (busy) return
    setSuccess(false)
    const validationError = validate()
    if (validationError !== null) {
      setError(validationError)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await devForgotPassword({
        email,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(true)
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err instanceof DevAuthError ? devAuthErrorMessage(err) : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-amber-700/60 bg-slate-800 p-8 shadow-xl">
          <div className="mb-4 rounded-lg border border-amber-600/50 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-400">
            Development / Testing Only
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Reset Password</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            This is a local testing convenience. It resets your password directly through the
            existing Supabase authentication system, with no OTP or email verification step.
          </p>

          {error !== null && (
            <div role="alert" className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
              {error}
            </div>
          )}
          {success && (
            <div role="status" className="mt-5 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
              Password reset successfully. You can now sign in with your new password.
            </div>
          )}

          <form className="mt-6 flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Email
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={busy}
                placeholder="student@college.edu"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              New password
              <input
                type="password"
                name="newPassword"
                required
                minLength={6}
                autoComplete="new-password"
                disabled={busy}
                placeholder="••••••••"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Confirm new password
              <input
                type="password"
                name="confirmPassword"
                required
                minLength={6}
                autoComplete="new-password"
                disabled={busy}
                placeholder="••••••••"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Resetting…' : 'Reset password'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={onBackToLogin}
              className="text-sm text-slate-400 hover:text-slate-200 underline"
            >
              Back to sign in
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

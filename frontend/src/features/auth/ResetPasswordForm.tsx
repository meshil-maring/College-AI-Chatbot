import { useEffect, useState } from 'react'
import PasswordField from './PasswordField.tsx'
import { AuthError, completePasswordReset } from '../../services/auth.ts'

export interface ResetPasswordFormProps {
  onBackToLogin: () => void
}

export default function ResetPasswordForm({ onBackToLogin }: ResetPasswordFormProps) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const token = fragment.get('access_token')
    const recovery = fragment.get('type') === 'recovery'
    window.history.replaceState(
      null,
      '',
      `${window.location.pathname}${window.location.search}`,
    )
    if (recovery && token) {
      setAccessToken(token)
    } else {
      setError('This password recovery link is invalid or has expired. Request a new link.')
    }
  }, [])

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (busy || accessToken === null) return
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setError(null)
    setBusy(true)
    try {
      await completePasswordReset(accessToken, newPassword, confirmPassword)
      setAccessToken(null)
      setNewPassword('')
      setConfirmPassword('')
      setCompleted(true)
    } catch (resetError) {
      setError(
        resetError instanceof AuthError
          ? resetError.message
          : 'Password reset could not be completed. Request a new link and try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white tracking-tight">Choose a new password</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Recovery is verified by the authentication provider. The link is single-use.
          </p>
          {error !== null && (
            <div role="alert" className="mt-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
              {error}
            </div>
          )}
          {completed && (
            <div role="status" className="mt-4 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
              Password reset successfully. Please sign in with your new password.
            </div>
          )}
          {!completed && accessToken !== null && (
            <form
              className="mt-6 flex flex-col gap-5"
              noValidate
              aria-busy={busy}
              onSubmit={(event) => void handleSubmit(event)}
            >
              <PasswordField
                label="New password"
                name="newPassword"
                value={newPassword}
                onChange={setNewPassword}
                required
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                disabled={busy}
              />
              <PasswordField
                label="Confirm new password"
                name="confirmPassword"
                value={confirmPassword}
                onChange={setConfirmPassword}
                required
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                disabled={busy}
              />
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy ? 'Resetting password…' : 'Reset password'}
              </button>
            </form>
          )}
          {(completed || accessToken === null) && (
            <button
              type="button"
              onClick={onBackToLogin}
              className="mt-6 w-full rounded-lg bg-slate-700 px-4 py-2 font-semibold text-white hover:bg-slate-600"
            >
              Back to Login
            </button>
          )}
        </div>
      </main>
    </div>
  )
}

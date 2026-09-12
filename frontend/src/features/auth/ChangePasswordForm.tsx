/**
 * DEVELOPMENT / TESTING ONLY — logged-in "Change Password" convenience.
 *
 * Only rendered when the backend reports `DEV_TEST_MODE=true` (see
 * `services/devAuth.ts` -> fetchDevAuthStatus). Requires the user to prove
 * their current password (verified server-side via Supabase's normal
 * sign-in-with-password flow) before the new password is applied through
 * the existing Supabase Auth admin API. No custom password storage.
 */

import { useState } from 'react'
import { useAuth } from './AuthProvider.tsx'
import { DevAuthError, devAuthErrorMessage, devChangePassword } from '../../services/devAuth.ts'

export default function ChangePasswordForm() {
  const { user } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const email = user?.email ?? null

  function validate(): string | null {
    if (email === null) {
      return 'Your account email could not be determined.'
    }
    if (currentPassword.length === 0) {
      return 'Please enter your current password.'
    }
    if (newPassword.length < 6) {
      return 'New password must be at least 6 characters.'
    }
    if (newPassword !== confirmPassword) {
      return 'Passwords do not match.'
    }
    return null
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (busy || email === null) return
    setSuccess(false)
    const validationError = validate()
    if (validationError !== null) {
      setError(validationError)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await devChangePassword({
        email,
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err instanceof DevAuthError ? devAuthErrorMessage(err) : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-2xl border border-amber-700/60 bg-slate-800 p-6 shadow-xl max-w-md">
      <div className="mb-4 rounded-lg border border-amber-600/50 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-400">
        Development / Testing Only
      </div>
      <h2 className="text-xl font-bold text-white tracking-tight">Change Password</h2>
      <p className="mt-2 text-sm text-slate-300">
        For local testing. Verifies your current password, then updates it through the existing
        Supabase authentication system.
      </p>

      {error !== null && (
        <div role="alert" className="mt-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div role="status" className="mt-4 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
          Password changed successfully.
        </div>
      )}

      <form className="mt-4 flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
        <label className="flex flex-col gap-1 text-sm text-slate-300">
          Current password
          <input
            type="password"
            name="currentPassword"
            required
            autoComplete="current-password"
            disabled={busy}
            className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
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
          {busy ? 'Changing…' : 'Change password'}
        </button>
      </form>
    </div>
  )
}

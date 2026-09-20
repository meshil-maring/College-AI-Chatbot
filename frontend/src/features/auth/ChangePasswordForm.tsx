/**
 * DEVELOPMENT / TESTING ONLY — logged-in "Change Password" convenience
 * (UX pass in Phase 6.15.6).
 *
 * Existing contract (audited, unchanged):
 *   POST /api/v1/dev/auth/change-password
 *     request : { email, current_password, new_password, confirm_password }
 *     success : 200 { message }
 *     gate    : DEV_TEST_MODE=false → 404 NOT_FOUND
 *
 * The current password is verified server-side through the normal Supabase
 * sign-in-with-password flow before the new password is applied through the
 * existing Supabase Auth admin API — no custom password storage.
 *
 * Session behaviour (taken from the backend contract, not assumed): the
 * backend performs NO session revocation when the password changes (there is
 * no revocation call anywhere and logout is client-side only for the
 * stateless JWT), so the CURRENT session stays valid and this form does not
 * sign the user out — AuthProvider state is untouched.
 *
 * Phase 6.15.6 additions: the shared PasswordField (visibility toggle),
 * per-field validation messages associated through aria-invalid /
 * aria-describedby, the "Updating…" loading label, aria-busy, and clearing of
 * all three plaintext fields once the operation completes.
 */

import { useState } from 'react'
import { useAuth } from './AuthProvider.tsx'
import PasswordField from './PasswordField.tsx'
import { DevAuthError, devAuthErrorMessage, devChangePassword } from '../../services/devAuth.ts'

interface FieldErrors {
  currentPassword?: string
  newPassword?: string
  confirmPassword?: string
}

export default function ChangePasswordForm() {
  const { user } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)

  const email = user?.email ?? null

  /** Client-side validation (UX only) — mirrors the backend contract. */
  function validate(): FieldErrors {
    const next: FieldErrors = {}
    if (currentPassword === '') {
      next.currentPassword = 'Please enter your current password.'
    }
    if (newPassword === '') {
      next.newPassword = 'Please enter a new password.'
    } else if (newPassword.length < 6) {
      next.newPassword = 'Password must be at least 6 characters.'
    }
    if (confirmPassword === '') {
      next.confirmPassword = 'Please confirm your new password.'
    } else if (newPassword !== confirmPassword) {
      next.confirmPassword = 'Passwords do not match.'
    }
    return next
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (busy) return
    if (email === null) {
      setFormError('Your account email could not be determined. Please sign in again.')
      return
    }
    setSuccess(false)
    setFormError(null)
    const fieldErrors = validate()
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors)
      return
    }
    setErrors({})
    setBusy(true)
    try {
      await devChangePassword({
        email,
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(true)
      // Phase 6.15.6 — drop every plaintext password from React state once the
      // operation completes (nothing is persisted or logged).
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setFormError(
        err instanceof DevAuthError
          ? devAuthErrorMessage(err)
          : 'Something went wrong. Please try again.',
      )
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

      {formError !== null && (
        <div role="alert" className="mt-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {formError}
        </div>
      )}
      {success && (
        <div role="status" className="mt-4 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
          Password changed successfully. Your session stays active.
        </div>
      )}

      <form
        className="mt-4 flex flex-col gap-4"
        noValidate
        aria-busy={busy}
        onSubmit={(event) => {
          void handleSubmit(event)
        }}
      >
        <PasswordField
          label="Current password"
          name="currentPassword"
          value={currentPassword}
          onChange={(value) => {
            setCurrentPassword(value)
            setErrors({})
          }}
          required
          autoComplete="current-password"
          disabled={busy}
          accent="amber"
          error={errors.currentPassword ?? null}
        />
        <PasswordField
          label="New password"
          name="newPassword"
          value={newPassword}
          onChange={(value) => {
            setNewPassword(value)
            setErrors({})
          }}
          required
          minLength={6}
          autoComplete="new-password"
          disabled={busy}
          accent="amber"
          error={errors.newPassword ?? null}
        />
        <PasswordField
          label="Confirm new password"
          name="confirmPassword"
          value={confirmPassword}
          onChange={(value) => {
            setConfirmPassword(value)
            setErrors({})
          }}
          required
          minLength={6}
          autoComplete="new-password"
          disabled={busy}
          accent="amber"
          error={errors.confirmPassword ?? null}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Updating…' : 'Change password'}
        </button>
      </form>
    </div>
  )
}

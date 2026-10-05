import { useState } from 'react'
import PasswordField from './PasswordField.tsx'
import { AuthError, changePassword } from '../../services/auth.ts'
import { useAuth } from './AuthProvider.tsx'

interface FieldErrors {
  currentPassword?: string
  newPassword?: string
  confirmPassword?: string
}

export default function ChangePasswordForm() {
  const { accessToken } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (busy) return
    const next: FieldErrors = {}
    if (!currentPassword) next.currentPassword = 'Please enter your current password.'
    if (newPassword.length < 8) next.newPassword = 'Password must be at least 8 characters.'
    else if (newPassword === currentPassword) {
      next.newPassword = 'Choose a new password different from your current password.'
    }
    if (!confirmPassword) {
      next.confirmPassword = 'Please confirm your new password.'
    } else if (confirmPassword !== newPassword) {
      next.confirmPassword = 'Passwords do not match.'
    }
    if (Object.keys(next).length > 0) {
      setErrors(next)
      return
    }
    if (accessToken === null) {
      setFormError('Your session has expired. Please sign in again.')
      return
    }

    setErrors({})
    setFormError(null)
    setSuccess(false)
    setBusy(true)
    try {
      await changePassword(accessToken, currentPassword, newPassword, confirmPassword)
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (changeError) {
      setFormError(
        changeError instanceof AuthError
          ? changeError.message
          : 'Password change could not be completed. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="max-w-md rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-xl">
      <h2 className="text-xl font-bold text-white tracking-tight">Change Password</h2>
      <p className="mt-2 text-sm text-slate-300">
        Verify your current password to update it. Other active sessions will be signed out.
      </p>
      {formError !== null && (
        <div role="alert" className="mt-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {formError}
        </div>
      )}
      {success && (
        <div role="status" className="mt-4 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
          Password changed successfully. This session remains active.
        </div>
      )}
      <form
        className="mt-4 flex flex-col gap-4"
        noValidate
        aria-busy={busy}
        onSubmit={(event) => void handleSubmit(event)}
      >
        <PasswordField
          label="Current password"
          name="currentPassword"
          value={currentPassword}
          onChange={setCurrentPassword}
          required
          autoComplete="current-password"
          disabled={busy}
          error={errors.currentPassword ?? null}
        />
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
          error={errors.newPassword ?? null}
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
          error={errors.confirmPassword ?? null}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Updating…' : 'Change password'}
        </button>
      </form>
    </section>
  )
}

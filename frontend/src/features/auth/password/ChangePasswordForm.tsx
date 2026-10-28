import { useState } from 'react'
import PasswordField from './PasswordField.tsx'
import { AuthError, changePassword } from '../../../services/auth/auth.ts'
import { useAuth } from '../session/AuthProvider.tsx'

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
    <section className="max-w-md rounded-xl border border-line bg-surface p-6 shadow-none">
      <h2 className="font-bold text-content tracking-tight text-section">Change Password</h2>
      <p className="mt-2 text-sm text-muted">
        Verify your current password to update it. Other active sessions will be signed out.
      </p>
      {formError !== null && (
        <div role="alert" className="mt-4 rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger">
          {formError}
        </div>
      )}
      {success && (
        <div
          role="status"
          className="mt-4 rounded-lg border border-success bg-success-bg px-4 py-2 text-sm text-success"
        >
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
          className="rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Updating…' : 'Change password'}
        </button>
      </form>
    </section>
  )
}

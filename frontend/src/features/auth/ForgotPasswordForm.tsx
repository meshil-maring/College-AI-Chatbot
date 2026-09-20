/**
 * DEVELOPMENT / TESTING ONLY — password recovery screen (Phase 6.15.6 UX pass).
 *
 * EXISTING RECOVERY ARCHITECTURE (audited — unchanged; the backend is the
 * source of truth):
 *
 *   POST /api/v1/dev/auth/forgot-password
 *     request : { email, new_password, confirm_password }
 *     success : 200 { message }   (generic — see "anti-enumeration" below)
 *     gate    : DEV_TEST_MODE=false → 404 NOT_FOUND (the feature is hidden)
 *
 * There is NO email/token-based recovery mechanism anywhere in this
 * application: the backend resets the password DIRECTLY through the existing
 * Supabase Auth admin API, so this screen collects the new password instead of
 * waiting for a reset link. Phase 6.15.6 does not invent one — a link/token
 * flow would require a backend endpoint that does not exist.
 *
 * Anti-enumeration (Phase 6.15.6):
 * - the backend returns the SAME generic 200 response for a known and an
 *   unknown email (app/api/dev_auth.py → _GENERIC_RECOVERY_MESSAGE);
 * - this screen never renders wording that confirms or denies that an account
 *   exists, and maps an unexpected account-related failure to a generic,
 *   non-disclosing message;
 * - no token is ever created and the user is NEVER authenticated here.
 *
 * Security: the plaintext password lives only in this component's state, is
 * cleared once the attempt completes, is sent only in the POST body, and is
 * never logged or placed in a URL.
 */

import { useState } from 'react'
import PasswordField from './PasswordField.tsx'
import { DevAuthError, devAuthErrorMessage, devForgotPassword } from '../../services/devAuth.ts'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const INPUT_CLASS =
  'rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400'

/**
 * Generic, enumeration-safe outcome shown after a submitted reset request. The
 * wording is identical whether or not an account exists, so the screen can
 * never be used to discover registered email addresses.
 */
export const RECOVERY_SUBMITTED_MESSAGE =
  'If an account exists for this email, the password has been reset. You can now sign in with your new password.'

/** Generic failure used for any unexpected account-related error. */
const GENERIC_RECOVERY_FAILURE =
  'We could not complete the password reset. Please try again.'

interface FieldErrors {
  email?: string
  newPassword?: string
  confirmPassword?: string
}

export interface ForgotPasswordFormProps {
  onBackToLogin: () => void
}

export default function ForgotPasswordForm({ onBackToLogin }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  /** Client-side validation (UX only) — mirrors the backend contract. */
  function validate(): FieldErrors {
    const next: FieldErrors = {}
    const trimmedEmail = email.trim()
    if (trimmedEmail === '') {
      next.email = 'Please enter your email address.'
    } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
      next.email = 'Please enter a valid email address.'
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

  /** Controlled, non-disclosing error text (never a raw backend message). */
  function messageFor(err: unknown): string {
    if (err instanceof DevAuthError) {
      // ANTI-ENUMERATION: an account-existence signal is never rendered.
      if (err.kind === 'user_not_found') return GENERIC_RECOVERY_FAILURE
      return devAuthErrorMessage(err)
    }
    return 'Something went wrong. Please try again.'
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (busy) return
    setSubmitted(false)
    setFormError(null)
    const fieldErrors = validate()
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors)
      return
    }
    setErrors({})
    setBusy(true)
    try {
      await devForgotPassword({
        email: email.trim(),
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSubmitted(true)
      // Phase 6.15.6 — drop the plaintext passwords from React state as soon
      // as the operation completes (they are never persisted anywhere).
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setFormError(messageFor(err))
    } finally {
      setBusy(false)
    }
  }


  // ---------------------------------------------------------------------------
  // Success state — generic, enumeration-safe, and NEVER an authentication:
  // no token is created and AuthProvider is untouched.
  // ---------------------------------------------------------------------------
  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <main className="max-w-md w-full py-16">
          <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
            <div className="mb-4 rounded-lg border border-amber-600/50 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-400">
              Development / Testing Only
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Password Reset Submitted
            </h1>
            <div
              role="status"
              className="mt-5 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400"
            >
              {RECOVERY_SUBMITTED_MESSAGE}
            </div>
            <p className="mt-4 text-sm text-slate-300 leading-relaxed">
              No email is sent by this development convenience: the password is
              updated directly through the existing Supabase authentication
              system.
            </p>
            <p className="mt-2 text-sm text-slate-300 leading-relaxed">
              This screen never reveals whether an account exists for the email
              you entered.
            </p>
            <button
              type="button"
              onClick={onBackToLogin}
              className="mt-6 w-full rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              Back to Login
            </button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <div className="mb-4 rounded-lg border border-amber-600/50 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-400">
            Development / Testing Only
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Reset Password</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Enter your email and choose a new password. This local testing
            convenience updates the password directly through the existing
            Supabase authentication system — no OTP or email step exists.
          </p>

          {formError !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400"
            >
              {formError}
            </div>
          )}

          <form
            className="mt-6 flex flex-col gap-5"
            noValidate
            aria-busy={busy}
            onSubmit={(event) => {
              void handleSubmit(event)
            }}
          >
            <div className="flex flex-col gap-1 text-sm text-slate-300">
              <label htmlFor="recovery-email">Email</label>
              <input
                id="recovery-email"
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={busy}
                placeholder="student@college.edu"
                className={INPUT_CLASS}
                value={email}
                aria-invalid={errors.email !== undefined ? true : undefined}
                aria-describedby={
                  errors.email !== undefined ? 'recovery-email-error' : undefined
                }
                onChange={(event) => {
                  setEmail(event.target.value)
                  setErrors({})
                }}
              />
              {errors.email !== undefined && (
                <p id="recovery-email-error" role="alert" className="text-sm text-red-400">
                  {errors.email}
                </p>
              )}
            </div>
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
              placeholder="••••••••"
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
              placeholder="••••••••"
              error={errors.confirmPassword ?? null}
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Resetting password…' : 'Reset password'}
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

/**
 * Phase 5.4 — Minimal login UI (extended by Phase 6.15.3).
 *
 * The primary identifier field accepts an email, a register number, or a
 * university roll number. Emails keep the existing POST /auth/login contract;
 * academic identifiers (register/roll numbers) require an institution code
 * (shown only then, per the backend contract) and go to
 * POST /auth/student/login. Routing happens in `services/auth/auth.ts`
 * (`authenticate`) — the form never decides identity semantics itself.
 * The JWT is never rendered, nothing is logged, and the password is never
 * persisted (it lives only in this component's state and is sent in the POST
 * body alone).
 *
 * Phase 6.15.6 additions (no architecture change):
 * - explicit client-side validation for the empty identifier / missing
 *   institution code / empty or too-short password, so the user gets the same
 *   user-safe vocabulary instead of a browser-native message;
 * - the shared `PasswordField` (visible label + show/hide toggle + error
 *   association through `aria-describedby`);
 * - a single alert region (`fieldError ?? authError`) and `aria-busy`.
 */

import { useState } from 'react'
import { useAuth } from '../session/AuthProvider.tsx'
import ForgotPasswordForm from '../password/ForgotPasswordForm.tsx'
import RegistrationForm from '../registration/RegistrationForm.tsx'
import PasswordField from '../password/PasswordField.tsx'
import { isEmailAddress } from '../../../services/auth/auth.ts'

export type LoginAudience = 'general' | 'student' | 'admin' | 'staff' | 'faculty' | 'super_admin'

const AUDIENCE_LABELS: Record<LoginAudience, string> = {
  general: 'Secure platform access',
  student: 'Student access',
  admin: 'University administrator access',
  staff: 'Staff access',
  faculty: 'Teacher / faculty access',
  super_admin: 'Platform administrator access',
}

export default function LoginForm({ audience = 'general' }: { audience?: LoginAudience }) {
  const { status, error, login } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [institutionCode, setInstitutionCode] = useState(
    () => new URLSearchParams(window.location.search).get('institution')?.trim().toUpperCase() ?? '',
  )
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [showRegistration, setShowRegistration] = useState(
    () =>
      (audience === 'student' || audience === 'faculty' || audience === 'staff') &&
      new URLSearchParams(window.location.search).get('register') === '1',
  )

  // An academic identifier (register number / university roll number) is
  // institution-scoped by the backend contract, so the institution code is
  // required — the field is shown only in that case (email login never needs
  // it, so email users see no extra field).
  const requiresInstitutionCode = identifier.trim() !== '' && !isEmailAddress(identifier.trim())

  const busy = status === 'authenticating'
  const showStudentApprovalHelp = audience === 'general' || audience === 'student'

  /**
   * Client-side validation is UX only (mirrors the backend rules: identifier
   * required, institution code required for academic identifiers, password
   * minimum length 6). The backend remains authoritative.
   */
  function validate(): string | null {
    if (identifier.trim() === '') {
      return 'Please enter your email, register number, or university roll number.'
    }
    if (requiresInstitutionCode && institutionCode.trim() === '') {
      return 'Please enter your institution code to sign in with a register number or roll number.'
    }
    if (password === '') {
      return 'Please enter your password.'
    }
    if (password.length < 6) {
      return 'Password must be at least 6 characters.'
    }
    return null
  }

  if (showRegistration) {
    return (
      <RegistrationForm
        onBackToLogin={() => setShowRegistration(false)}
        registrationType={audience === 'faculty' ? 'faculty' : audience === 'staff' ? 'staff' : 'student'}
      />
    )
  }

  if (showForgotPassword) {
    return <ForgotPasswordForm onBackToLogin={() => setShowForgotPassword(false)} />
  }

  // ONE alert region: a freshly produced validation message takes precedence
  // over the last authentication error held by AuthProvider.
  const displayedError = fieldError ?? error

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-xl border border-line bg-surface p-8 shadow-none">
          <a
            href="/"
            className="mb-5 inline-block rounded-sm text-sm text-muted underline hover:text-content focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Back to platform gateway
          </a>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">{AUDIENCE_LABELS[audience]}</p>
          <h1 className="font-bold text-content tracking-tight text-page">College AI Chatbot</h1>
          <p className="mt-2 text-sm text-muted leading-relaxed">Sign in with your account details to continue.</p>
          {showStudentApprovalHelp && (
            <p id="student-approval-help" className="mt-3 text-sm text-muted leading-relaxed">
              New student accounts need institutional approval before signing in. For questions about your registration
              or account access, contact your institution administrator.
            </p>
          )}

          {displayedError !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger"
            >
              {displayedError}
            </div>
          )}

          <form
            className="mt-6 flex flex-col gap-5"
            noValidate
            aria-busy={busy}
            onSubmit={(event) => {
              event.preventDefault()
              if (busy) return
              const validationError = validate()
              if (validationError !== null) {
                setFieldError(validationError)
                return
              }
              setFieldError(null)
              void login(identifier, password, institutionCode || undefined)
            }}
          >
            <label className="flex flex-col gap-1 text-sm text-muted">
              Email, Register Number or University Roll Number
              <input
                type="text"
                name="identifier"
                required
                autoComplete="username"
                aria-describedby={showStudentApprovalHelp ? 'student-approval-help' : undefined}
                disabled={busy}
                placeholder="student@college.edu or REG2026001"
                className="rounded-lg border border-control bg-surface px-3 py-2 text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                value={identifier}
                onChange={(event) => {
                  setIdentifier(event.target.value)
                  setFieldError(null)
                }}
              />
            </label>
            {requiresInstitutionCode && (
              <>
                <label className="flex flex-col gap-1 text-sm text-muted">
                  Institution Code
                  <input
                    type="text"
                    name="institution_code"
                    required
                    autoComplete="off"
                    disabled={busy}
                    placeholder="e.g., GIT"
                    className="rounded-lg border border-control bg-surface px-3 py-2 text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    value={institutionCode}
                    onChange={(event) => {
                      setInstitutionCode(event.target.value)
                      setFieldError(null)
                    }}
                  />
                </label>
                <p className="-mt-3 text-xs text-muted">
                  Required when signing in with a register number or roll number.
                </p>
              </>
            )}
            <PasswordField
              label="Password"
              name="password"
              value={password}
              onChange={(value) => {
                setPassword(value)
                setFieldError(null)
              }}
              required
              minLength={6}
              maxLength={128}
              autoComplete="current-password"
              disabled={busy}
              placeholder="••••••••"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setShowForgotPassword(true)}
              className="text-sm text-muted hover:text-content underline"
            >
              Forgot password?
            </button>
          </form>

          <p className="mt-6 text-sm text-muted">
            Don't have an account?{' '}
            <button
              type="button"
              disabled={busy}
              onClick={() => setShowRegistration(true)}
              className="font-medium text-accent underline hover:text-accent-hover"
            >
              {audience === 'faculty'
                ? 'Register as Faculty'
                : audience === 'staff'
                  ? 'Register as Staff'
                  : 'Register as Student'}
            </button>
          </p>
        </div>
      </main>
    </div>
  )
}

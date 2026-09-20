/**
 * Phase 5.4 — Minimal login UI (extended by Phase 6.15.3).
 *
 * The primary identifier field accepts an email, a register number, or a
 * university roll number. Emails keep the existing POST /auth/login contract;
 * academic identifiers (register/roll numbers) require an institution code
 * (shown only then, per the backend contract) and go to
 * POST /auth/student/login. Routing happens in `services/auth.ts`
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

import { useEffect, useState } from 'react'
import { useAuth } from './AuthProvider.tsx'
import ForgotPasswordForm from './ForgotPasswordForm.tsx'
import RegistrationForm from './RegistrationForm.tsx'
import PasswordField from './PasswordField.tsx'
import { isEmailAddress } from '../../services/auth.ts'
import { fetchDevAuthStatus } from '../../services/devAuth.ts'

export default function LoginForm() {
  const { status, error, login } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [institutionCode, setInstitutionCode] = useState('')
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [showRegistration, setShowRegistration] = useState(false)
  const [devTestModeEnabled, setDevTestModeEnabled] = useState(false)

  // An academic identifier (register number / university roll number) is
  // institution-scoped by the backend contract, so the institution code is
  // required — the field is shown only in that case (email login never needs
  // it, so email users see no extra field).
  const requiresInstitutionCode =
    identifier.trim() !== '' && !isEmailAddress(identifier.trim())

  useEffect(() => {
    // DEVELOPMENT / TESTING ONLY — "Forgot Password?" only appears when the
    // backend explicitly reports dev/test mode is enabled.
    let cancelled = false
    void fetchDevAuthStatus().then((result) => {
      if (!cancelled) setDevTestModeEnabled(result.dev_test_mode)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const busy = status === 'authenticating'

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
    return <RegistrationForm onBackToLogin={() => setShowRegistration(false)} />
  }

  if (showForgotPassword) {
    return <ForgotPasswordForm onBackToLogin={() => setShowForgotPassword(false)} />
  }

  // ONE alert region: a freshly produced validation message takes precedence
  // over the last authentication error held by AuthProvider.
  const displayedError = fieldError ?? error

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Sign in to continue. Authentication is handled entirely by the backend.
          </p>

          {displayedError !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400"
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
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Email, Register Number or University Roll Number
              <input
                type="text"
                name="identifier"
                required
                autoComplete="username"
                disabled={busy}
                placeholder="student@college.edu or REG2026001"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={identifier}
                onChange={(event) => {
                  setIdentifier(event.target.value)
                  setFieldError(null)
                }}
              />
            </label>
            {requiresInstitutionCode && (
              <>
                <label className="flex flex-col gap-1 text-sm text-slate-300">
                  Institution Code
                  <input
                    type="text"
                    name="institution_code"
                    required
                    autoComplete="off"
                    disabled={busy}
                    placeholder="e.g., GIT"
                    className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                    value={institutionCode}
                    onChange={(event) => {
                      setInstitutionCode(event.target.value)
                      setFieldError(null)
                    }}
                  />
                </label>
                <p className="-mt-3 text-xs text-slate-500">
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
              autoComplete="current-password"
              disabled={busy}
              placeholder="••••••••"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
            {devTestModeEnabled && (
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowForgotPassword(true)}
                className="text-sm text-slate-400 hover:text-slate-200 underline"
              >
                Forgot password? (Dev/Test only)
              </button>
            )}
          </form>

          <p className="mt-6 text-sm text-slate-400">
            Don't have an account?{' '}
            <button
              type="button"
              disabled={busy}
              onClick={() => setShowRegistration(true)}
              className="font-medium text-emerald-400 underline hover:text-emerald-300"
            >
              Register as Student
            </button>
          </p>
        </div>
      </main>
    </div>
  )
}
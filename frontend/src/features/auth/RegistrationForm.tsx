/**
 * Phase 6.15.2 — Student registration UI.
 *
 * Collects exactly the fields the backend registration contract accepts
 * (POST /api/v1/users/register, registration_type='student') and resolves
 * the institution code through the public read-only lookup endpoint
 * (GET /api/v1/institutions/lookup) BEFORE the form can be submitted.
 *
 * Contract invariants:
 * - The backend resolves `institution_code` server-side; this form never
 *   sends (or trusts) a user-supplied institution UUID.
 * - At least one academic identifier (register number OR university roll
 *   number) is required — mirrors the backend IDENTIFIER_REQUIRED rule.
 * - Password minimum length 6 — mirrors the backend validator.
 * - A successful registration ALWAYS yields approval_status='pending'; the
 *   response carries no token, so the student is NOT treated as logged in.
 *
 * Design follows the existing auth screens (LoginForm / ForgotPasswordForm):
 * Tailwind slate/emerald, wrapped labels, role="alert"/"status" regions,
 * disabled controls while an operation is active.
 *
 * Phase 6.15.6: the two password inputs use the shared `PasswordField`
 * (explicit label association, show/hide toggle, error association) and the
 * form reports `aria-busy` while the registration request is in flight. The
 * registration contract itself is unchanged.
 */

import { useState } from 'react'
import PasswordField from './PasswordField.tsx'
import {
  RegistrationError,
  lookupInstitution,
  registerStudent,
  registrationErrorMessage,
} from '../../services/registration.ts'
import type {
  InstitutionLookupResponse,
  RegistrationResponse,
} from '../../types/registration.ts'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const INPUT_CLASS =
  'rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400'

/** States of the institution-code resolution UX. */
type InstitutionStatus =
  | 'idle'
  | 'checking'
  | 'found'
  | 'invalid'
  | 'not_accepting'
  | 'error'

export interface RegistrationFormProps {
  /** Navigate back to the login screen (existing conditional navigation). */
  onBackToLogin: () => void
}

export default function RegistrationForm({ onBackToLogin }: RegistrationFormProps) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [registerNumber, setRegisterNumber] = useState('')
  const [universityRollNumber, setUniversityRollNumber] = useState('')
  const [institutionCode, setInstitutionCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [resolvedInstitution, setResolvedInstitution] =
    useState<InstitutionLookupResponse | null>(null)
  const [institutionStatus, setInstitutionStatus] =
    useState<InstitutionStatus>('idle')
  const [institutionMessage, setInstitutionMessage] = useState<string | null>(null)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<RegistrationResponse | null>(null)

  /** True when the stored resolution belongs to the currently typed code. */
  function isResolvedFor(code: string): boolean {
    return (
      resolvedInstitution !== null &&
      resolvedInstitution.code.toUpperCase() === code.trim().toUpperCase()
    )
  }

  /** Clear the resolution when the code field is emptied. */
  function handleInstitutionBlur(): void {
    const code = institutionCode.trim()
    if (code.length === 0) {
      setResolvedInstitution(null)
      setInstitutionStatus('idle')
      setInstitutionMessage(null)
      return
    }
    if (!isResolvedFor(code)) {
      void resolveInstitution(code)
    }
  }

  /**
   * Resolve the typed institution code through the public lookup endpoint.
   * Raw API errors are never surfaced — only the controlled messages below.
   */
  async function resolveInstitution(
    rawCode: string,
  ): Promise<InstitutionLookupResponse | null> {
    const code = rawCode.trim()
    if (code.length < 2) {
      setResolvedInstitution(null)
      setInstitutionStatus('invalid')
      setInstitutionMessage('Enter your institution code (e.g. ABC001).')
      return null
    }
    setInstitutionStatus('checking')
    setInstitutionMessage('Finding institution…')
    try {
      const found = await lookupInstitution(code)
      setResolvedInstitution(found)
      setInstitutionStatus('found')
      setInstitutionMessage(null)
      return found
    } catch (err) {
      setResolvedInstitution(null)
      if (err instanceof RegistrationError) {
        if (err.kind === 'institution_not_found') {
          setInstitutionStatus('invalid')
          setInstitutionMessage(
            'Institution code was not found. Please check the code and try again.',
          )
          return null
        }
        if (err.kind === 'institution_not_accepting') {
          setInstitutionStatus('not_accepting')
          setInstitutionMessage(
            'This institution is not currently accepting registrations.',
          )
          return null
        }
        setInstitutionStatus('error')
        setInstitutionMessage(registrationErrorMessage(err))
        return null
      }
      setInstitutionStatus('error')
      setInstitutionMessage(
        'Could not verify the institution code right now. Please try again.',
      )
      return null
    }
  }

  /**
   * Client-side validation mirroring the backend contract exactly — never
   * stricter (password >= 6; names non-blank; at least one academic
   * identifier required).
   */
  function validate(): string | null {
    if (fullName.trim().length < 2) {
      return 'Please enter your full name.'
    }
    if (!EMAIL_PATTERN.test(email.trim())) {
      return 'Please enter a valid email address.'
    }
    if (registerNumber.trim() === '' && universityRollNumber.trim() === '') {
      return 'Enter at least one of register number or university roll number.'
    }
    if (institutionCode.trim().length < 2) {
      return 'Enter your institution code (e.g. ABC001).'
    }
    if (password.length < 6) {
      return 'Password must be at least 6 characters.'
    }
    if (confirmPassword !== password) {
      return 'Passwords do not match.'
    }
    return null
  }

  /**
   * Split the single Full Name field into the backend's required first_name /
   * last_name. With one token only, the token is reused as the last name so
   * the backend's non-blank rule is met without rejecting the student.
   */
  function splitFullName(
    value: string,
  ): { first_name: string; last_name: string } {
    const tokens = value.trim().split(/\s+/)
    const first = tokens[0] ?? ''
    const rest = tokens.slice(1).join(' ')
    return { first_name: first, last_name: rest || first }
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (submitting) return
    setError(null)
    const validationError = validate()
    if (validationError !== null) {
      setError(validationError)
      return
    }

    setSubmitting(true)
    try {
      const code = institutionCode.trim()
      // Registration must never submit with an unverified institution:
      // resolve on demand when the code changed (or was never looked up).
      const resolved =
        isResolvedFor(code) ? resolvedInstitution : await resolveInstitution(code)
      if (resolved === null) {
        return // the institution status region already explains the problem
      }
      const { first_name, last_name } = splitFullName(fullName)
      const response = await registerStudent({
        registration_type: 'student',
        institution_code: resolved.code,
        email: email.trim(),
        password,
        first_name,
        last_name,
        register_number: registerNumber.trim() || null,
        university_roll_number: universityRollNumber.trim() || null,
      })
      // Pending-approval state ONLY: the response carries no token and the
      // auth state is untouched, so the student is never treated as logged in.
      setSuccess(response)
      // Phase 6.15.5 hardening (browser-storage/memory audit §20): the
      // plaintext password is dropped immediately after the submission
      // completes — it is never needed again once the account exists, and
      // it must not linger in component memory on the success screen.
      setPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(
        err instanceof RegistrationError
          ? registrationErrorMessage(err)
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (success !== null) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <main className="max-w-md w-full py-16">
          <div className="rounded-2xl border border-emerald-700/60 bg-slate-800 p-8 shadow-xl">
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Registration Successful
            </h1>
            <div
              role="status"
              className="mt-5 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400"
            >
              Your student account has been created.
            </div>
            <p className="mt-4 text-sm text-slate-300 leading-relaxed">
              Your account is currently waiting for approval from your college
              administrator or staff.
            </p>
            <p className="mt-2 text-sm text-slate-300 leading-relaxed">
              You will be able to log in after your account has been approved.
            </p>
            <button
              type="button"
              onClick={onBackToLogin}
              className="mt-6 w-full rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500"
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
          <h1 className="text-3xl font-bold text-white tracking-tight">
            College AI Chatbot
          </h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Student Registration. Registration is handled entirely by the
            backend; your account is reviewed by your college before you can
            sign in.
          </p>

          {error !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400"
            >
              {error}
            </div>
          )}

          <form
            className="mt-6 flex flex-col gap-5"
            onSubmit={(event) => {
              void handleSubmit(event)
            }}
            noValidate
            aria-busy={submitting}
          >
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Full Name
              <input
                type="text"
                name="fullName"
                required
                autoComplete="name"
                disabled={submitting}
                placeholder="Jane Doe"
                className={INPUT_CLASS}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Email
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={submitting}
                placeholder="student@college.edu"
                className={INPUT_CLASS}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Register Number
              <input
                type="text"
                name="registerNumber"
                autoComplete="off"
                disabled={submitting}
                placeholder="e.g. 1001"
                className={INPUT_CLASS}
                value={registerNumber}
                onChange={(event) => setRegisterNumber(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              University Roll Number
              <input
                type="text"
                name="universityRollNumber"
                autoComplete="off"
                disabled={submitting}
                placeholder="e.g. 2026-1001"
                className={INPUT_CLASS}
                value={universityRollNumber}
                onChange={(event) => setUniversityRollNumber(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Institution Code
              <input
                type="text"
                name="institutionCode"
                required
                autoComplete="off"
                disabled={submitting}
                placeholder="ABC001"
                className={INPUT_CLASS}
                aria-describedby="institution-status"
                value={institutionCode}
                onChange={(event) => {
                  setInstitutionCode(event.target.value)
                  // Typing invalidates the previous resolution; the code is
                  // re-verified on blur (or right before submission).
                  setResolvedInstitution(null)
                  setInstitutionStatus('idle')
                  setInstitutionMessage(null)
                }}
                onBlur={handleInstitutionBlur}
              />
            </label>
            <div id="institution-status" aria-live="polite">
              {institutionStatus === 'checking' && (
                <p role="status" className="text-sm text-slate-400">
                  Finding institution…
                </p>
              )}
              {institutionStatus === 'found' && resolvedInstitution !== null && (
                <p role="status" className="text-sm text-emerald-400">
                  {resolvedInstitution.name}
                </p>
              )}
              {(institutionStatus === 'invalid' ||
                institutionStatus === 'not_accepting' ||
                institutionStatus === 'error') &&
                institutionMessage !== null && (
                  <p role="alert" className="text-sm text-red-400">
                    {institutionMessage}
                  </p>
                )}
            </div>
            <PasswordField
              label="Password"
              name="password"
              value={password}
              onChange={setPassword}
              required
              minLength={6}
              autoComplete="new-password"
              disabled={submitting}
              placeholder="••••••••"
            />
            <PasswordField
              label="Confirm Password"
              name="confirmPassword"
              value={confirmPassword}
              onChange={setConfirmPassword}
              required
              minLength={6}
              autoComplete="new-password"
              disabled={submitting}
              placeholder="••••••••"
            />
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? 'Creating account…' : 'Create Account'}
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={onBackToLogin}
              className="text-sm text-slate-400 hover:text-slate-200 underline"
            >
              Already have an account? Back to Login
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

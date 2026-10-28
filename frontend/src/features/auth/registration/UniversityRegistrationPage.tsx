import { useState } from 'react'
import PasswordField from '../password/PasswordField.tsx'
import {
  registerUniversity,
  UniversityRegistrationError,
  type UniversityRegistrationResponse,
} from '../../../services/registration/universityRegistration.ts'

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PLATFORM_ORGANIZATION_CODE = 'COLLEGE-AI-PLATFORM'
const inputClass =
  'rounded-lg border border-control bg-canvas px-3 py-3 text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent'
const labelClass = 'flex flex-col gap-2 text-sm font-medium text-muted'

export default function UniversityRegistrationPage() {
  const [form, setForm] = useState({
    name: '',
    institutionCode: '',
    officialEmail: '',
    location: '',
    adminFirstName: '',
    adminLastName: '',
    adminEmail: '',
    password: '',
    confirmPassword: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<UniversityRegistrationResponse | null>(null)

  const update = (field: keyof typeof form, value: string): void => {
    setForm((current) => ({ ...current, [field]: value }))
    setError(null)
  }

  function validate(): string | null {
    if (form.name.trim().length < 2) return 'Enter the university name.'
    if (form.institutionCode.trim().length < 2) return 'Enter a university code of at least 2 characters.'
    if (!EMAIL.test(form.officialEmail.trim())) return 'Enter a valid official university email.'
    if (form.adminFirstName.trim() === '' || form.adminLastName.trim() === '')
      return 'Enter the administrator’s first and last name.'
    if (!EMAIL.test(form.adminEmail.trim())) return 'Enter a valid administrator email.'
    if (form.password.length < 8) return 'Choose a password of at least 8 characters.'
    if (form.password !== form.confirmPassword) return 'The two passwords do not match.'
    return null
  }

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (submitting) return
    const validationError = validate()
    if (validationError !== null) {
      setError(validationError)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await registerUniversity({
        name: form.name.trim(),
        institution_code: form.institutionCode.trim().toUpperCase(),
        // Public SaaS registrations join the reserved platform-owned
        // onboarding organization and are activated server-side immediately.
        organization_code: PLATFORM_ORGANIZATION_CODE,
        official_email: form.officialEmail.trim().toLowerCase(),
        ...(form.location.trim() ? { location: form.location.trim() } : {}),
        admin_email: form.adminEmail.trim().toLowerCase(),
        admin_password: form.password,
        admin_first_name: form.adminFirstName.trim(),
        admin_last_name: form.adminLastName.trim(),
      })
      setForm((current) => ({ ...current, password: '', confirmPassword: '' }))
      setSuccess(result)
    } catch (caught) {
      setError(caught instanceof UniversityRegistrationError ? caught.message : 'Registration could not be completed.')
    } finally {
      setSubmitting(false)
    }
  }

  if (success !== null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
        <section className="w-full max-w-xl rounded-xl border border-success bg-surface p-8 shadow-none">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-success">Registration complete</p>
          <h1 className="mt-2 font-bold text-content text-page">Your university is ready</h1>
          <p role="status" className="mt-4 leading-7 text-muted">
            {success.message}
          </p>
          <p className="mt-3 text-sm text-muted">
            University code: <strong className="text-content">{success.institution_code}</strong>
          </p>
          <p className="mt-2 text-sm text-muted">Your University Admin account is active. You can sign in now.</p>
          <div className="mt-7 flex gap-3">
            <a href="/login/admin" className="rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-ink">
              Admin login
            </a>
            <a href="/" className="rounded-lg border border-control px-4 py-3 text-sm font-semibold text-content">
              Home
            </a>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-canvas px-6 py-12 text-content">
      <section className="mx-auto w-full max-w-3xl rounded-xl border border-line bg-surface p-8 shadow-none">
        <a href="/" className="text-sm text-muted underline hover:text-content">
          Back to home
        </a>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-accent">University onboarding</p>
        <h1 className="mt-2 font-bold text-content text-page">Register your university</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
          Create your university and its initial University Admin account. No Platform Manager approval is required.
        </p>

        {error ? (
          <div role="alert" className="mt-5 rounded-lg border border-danger bg-danger-bg px-4 py-3 text-sm text-danger">
            {error}
          </div>
        ) : null}

        <form
          className="mt-7 space-y-7"
          aria-busy={submitting}
          onSubmit={(event) => {
            void submit(event)
          }}
        >
          <fieldset className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
            <legend className="col-span-full mb-3 text-lg font-semibold text-content">University details</legend>
            <label className={`${labelClass} sm:col-span-2`}>
              University name
              <input
                className={inputClass}
                value={form.name}
                onChange={(e) => update('name', e.target.value)}
                required
              />
            </label>
            <label className={labelClass}>
              University code
              <input
                className={inputClass}
                value={form.institutionCode}
                onChange={(e) => update('institutionCode', e.target.value)}
                placeholder="e.g. ABCU"
                required
              />
            </label>
            <label className={labelClass}>
              Official university email
              <input
                type="email"
                className={inputClass}
                value={form.officialEmail}
                onChange={(e) => update('officialEmail', e.target.value)}
                required
              />
            </label>
            <div className="rounded-lg border border-line bg-canvas px-4 py-3 sm:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Registration network</p>
              <p className="mt-1 text-sm font-medium text-content">College AI Platform</p>
              <p className="mt-1 text-xs leading-5 text-muted">
                Your university will be activated immediately after registration.
              </p>
            </div>
            <label className={`${labelClass} sm:col-span-2`}>
              Location (optional)
              <input
                className={inputClass}
                value={form.location}
                onChange={(e) => update('location', e.target.value)}
              />
            </label>
          </fieldset>

          <fieldset className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
            <legend className="col-span-full mb-3 text-lg font-semibold text-content">Initial University Admin</legend>
            <label className={labelClass}>
              First name
              <input
                autoComplete="given-name"
                className={inputClass}
                value={form.adminFirstName}
                onChange={(e) => update('adminFirstName', e.target.value)}
                required
              />
            </label>
            <label className={labelClass}>
              Last name
              <input
                autoComplete="family-name"
                className={inputClass}
                value={form.adminLastName}
                onChange={(e) => update('adminLastName', e.target.value)}
                required
              />
            </label>
            <label className={`${labelClass} sm:col-span-2`}>
              Admin email
              <input
                type="email"
                autoComplete="email"
                className={inputClass}
                value={form.adminEmail}
                onChange={(e) => update('adminEmail', e.target.value)}
                required
              />
            </label>
            <PasswordField
              label="Password"
              name="university-admin-password"
              value={form.password}
              onChange={(value) => update('password', value)}
              minLength={8}
              autoComplete="new-password"
              required
              disabled={submitting}
            />
            <PasswordField
              label="Confirm password"
              name="university-admin-password-confirmation"
              value={form.confirmPassword}
              onChange={(value) => update('confirmPassword', value)}
              minLength={8}
              autoComplete="new-password"
              required
              disabled={submitting}
            />
          </fieldset>

          <p className="rounded-lg border border-line bg-canvas px-4 py-3 text-xs leading-5 text-muted">
            The password is sent only to the authentication service. Role, scope, institution status, and approval state
            are assigned by the backend and cannot be selected in this form.
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-accent px-5 py-3 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? 'Registering university…' : 'Register university'}
          </button>
        </form>
      </section>
    </main>
  )
}

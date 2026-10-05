import { useState } from 'react'
import PasswordField from './PasswordField.tsx'
import {
  registerUniversity,
  UniversityRegistrationError,
  type UniversityRegistrationResponse,
} from '../../services/universityRegistration.ts'

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PLATFORM_ORGANIZATION_CODE = 'COLLEGE-AI-PLATFORM'
const inputClass = 'rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400'
const labelClass = 'flex flex-col gap-1.5 text-sm font-medium text-slate-300'

export default function UniversityRegistrationPage() {
  const [form, setForm] = useState({
    name: '', institutionCode: '', officialEmail: '',
    location: '', adminFirstName: '', adminLastName: '', adminEmail: '', password: '', confirmPassword: '',
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
    if (form.adminFirstName.trim() === '' || form.adminLastName.trim() === '') return 'Enter the administrator’s first and last name.'
    if (!EMAIL.test(form.adminEmail.trim())) return 'Enter a valid administrator email.'
    if (form.password.length < 8) return 'Choose a password of at least 8 characters.'
    if (form.password !== form.confirmPassword) return 'The two passwords do not match.'
    return null
  }

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (submitting) return
    const validationError = validate()
    if (validationError !== null) { setError(validationError); return }
    setSubmitting(true)
    setError(null)
    try {
      const result = await registerUniversity({
        name: form.name.trim(),
        institution_code: form.institutionCode.trim().toUpperCase(),
        // Public SaaS registrations always join the platform-owned onboarding
        // organization. Users cannot guess or select another tenant here.
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
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
        <section className="w-full max-w-xl rounded-2xl border border-emerald-500/30 bg-slate-900 p-8 shadow-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Registration submitted</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Your university is pending approval</h1>
          <p role="status" className="mt-4 leading-7 text-slate-300">{success.message}</p>
          <p className="mt-3 text-sm text-slate-400">University code: <strong className="text-slate-200">{success.institution_code}</strong></p>
          <p className="mt-2 text-sm text-slate-400">You can sign in after the organization approves and activates the university.</p>
          <div className="mt-7 flex gap-3">
            <a href="/login/admin" className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white">Admin login</a>
            <a href="/" className="rounded-lg border border-slate-600 px-4 py-2.5 text-sm font-semibold text-slate-200">Home</a>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-slate-100">
      <section className="mx-auto w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <a href="/" className="text-sm text-slate-400 underline hover:text-white">Back to home</a>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">University onboarding</p>
        <h1 className="mt-2 text-3xl font-bold text-white">Register your university</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Create the initial University Admin account and submit your university for approval. Access remains disabled until the owning organization approves the request.</p>

        {error ? <div role="alert" className="mt-5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div> : null}

        <form className="mt-7 space-y-7" aria-busy={submitting} onSubmit={(event) => { void submit(event) }}>
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="col-span-full mb-3 text-lg font-semibold text-white">University details</legend>
            <label className={`${labelClass} sm:col-span-2`}>University name<input className={inputClass} value={form.name} onChange={(e) => update('name', e.target.value)} required /></label>
            <label className={labelClass}>University code<input className={inputClass} value={form.institutionCode} onChange={(e) => update('institutionCode', e.target.value)} placeholder="e.g. ABCU" required /></label>
            <label className={labelClass}>Official university email<input type="email" className={inputClass} value={form.officialEmail} onChange={(e) => update('officialEmail', e.target.value)} required /></label>
            <div className="rounded-lg border border-slate-700 bg-slate-950/60 px-4 py-3 sm:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Registration network</p>
              <p className="mt-1 text-sm font-medium text-slate-200">College AI Platform</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">Your university will be submitted to the platform approval queue automatically.</p>
            </div>
            <label className={`${labelClass} sm:col-span-2`}>Location (optional)<input className={inputClass} value={form.location} onChange={(e) => update('location', e.target.value)} /></label>
          </fieldset>

          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="col-span-full mb-3 text-lg font-semibold text-white">Initial University Admin</legend>
            <label className={labelClass}>First name<input autoComplete="given-name" className={inputClass} value={form.adminFirstName} onChange={(e) => update('adminFirstName', e.target.value)} required /></label>
            <label className={labelClass}>Last name<input autoComplete="family-name" className={inputClass} value={form.adminLastName} onChange={(e) => update('adminLastName', e.target.value)} required /></label>
            <label className={`${labelClass} sm:col-span-2`}>Admin email<input type="email" autoComplete="email" className={inputClass} value={form.adminEmail} onChange={(e) => update('adminEmail', e.target.value)} required /></label>
            <PasswordField label="Password" name="university-admin-password" value={form.password} onChange={(value) => update('password', value)} minLength={8} autoComplete="new-password" required disabled={submitting} />
            <PasswordField label="Confirm password" name="university-admin-password-confirmation" value={form.confirmPassword} onChange={(value) => update('confirmPassword', value)} minLength={8} autoComplete="new-password" required disabled={submitting} />
          </fieldset>

          <p className="rounded-lg border border-slate-700 bg-slate-950/60 px-4 py-3 text-xs leading-5 text-slate-400">The password is sent only to the authentication service. Role, scope, institution status, and approval state are assigned by the backend and cannot be selected in this form.</p>
          <button type="submit" disabled={submitting} className="w-full rounded-lg bg-emerald-600 px-5 py-3 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60">{submitting ? 'Submitting registration…' : 'Submit university registration'}</button>
        </form>
      </section>
    </main>
  )
}

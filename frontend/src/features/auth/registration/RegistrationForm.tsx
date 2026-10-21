import { RegistrationFields } from './RegistrationFields.tsx'
import { RegistrationSuccess } from './RegistrationSuccess.tsx'
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
 * - Password minimum length 8 — mirrors the backend validator.
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

import { useRegistrationForm } from './useRegistrationForm.ts'
export type { RegistrationFormProps } from './useRegistrationForm.ts'

export default function RegistrationForm(props: Parameters<typeof useRegistrationForm>[0]) {
  const model = useRegistrationForm(props)
  const { registrationType, error, success } = model

  if (success !== null) {
    return <RegistrationSuccess model={model} />
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            {registrationType === 'student' ? 'Student' : registrationType === 'faculty' ? 'Faculty' : 'Staff'}{' '}
            Registration. Submit your details for review by your institution before signing in.
          </p>

          {error !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400"
            >
              {error}
            </div>
          )}

          <RegistrationFields model={model} />
        </div>
      </main>
    </div>
  )
}

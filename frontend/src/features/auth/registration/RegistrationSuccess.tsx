import type { RegistrationFormModel } from './useRegistrationForm.ts'

export function RegistrationSuccess({ model }: { model: RegistrationFormModel }) {
  const { onBackToLogin, registrationType, resolvedInstitution, success, confirmationTitleRef } = model
  if (success === null) return null
  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-xl border border-success bg-surface p-8 shadow-none">
          <h1
            ref={confirmationTitleRef}
            tabIndex={-1}
            className="font-bold text-content tracking-tight focus:outline-none text-page"
          >
            Registration Successful
          </h1>
          <div
            role="status"
            aria-atomic="true"
            className="mt-5 rounded-lg border border-success bg-success-bg px-4 py-2 text-sm text-success"
          >
            <p>
              {registrationType === 'student'
                ? 'Your student account has been created.'
                : `Your ${registrationType} registration has been submitted.`}
            </p>
            <p className="mt-1 font-semibold">Awaiting institutional approval</p>
          </div>
          <p className="mt-4 text-sm text-muted leading-relaxed">
            Your registration has been submitted to{' '}
            <span className="font-semibold text-content">{resolvedInstitution?.name ?? success.institution_code}</span>.
          </p>
          <p className="mt-2 text-sm text-muted leading-relaxed">
            {registrationType === 'student'
              ? 'An institution administrator or authorized staff member will review your student account.'
              : 'Your institution administrator will review your registration.'}{' '}
            You can sign in after your account has been approved.
          </p>
          <p className="mt-2 text-sm text-muted leading-relaxed">
            If you receive a confirmation email, use its link to verify your email address. Email verification is
            separate from institutional approval.
          </p>
          {registrationType === 'student' && (
            <p className="mt-2 text-sm text-muted leading-relaxed">
              After approval, return to login with your email, register number, or university roll number. Your
              institution code is <span className="font-semibold text-content">{success.institution_code}</span>.
            </p>
          )}
          <p className="mt-2 text-sm text-muted leading-relaxed">
            For questions about your registration, contact your institution administrator.
          </p>
          <button
            type="button"
            onClick={onBackToLogin}
            className="mt-6 w-full rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Back to Login
          </button>
        </div>
      </main>
    </div>
  )
}

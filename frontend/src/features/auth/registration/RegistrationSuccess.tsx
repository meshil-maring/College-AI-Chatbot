import type { RegistrationFormModel } from './useRegistrationForm.ts'

export function RegistrationSuccess({ model }: { model: RegistrationFormModel }) {
  const { onBackToLogin, registrationType, resolvedInstitution, success, confirmationTitleRef } = model
  if (success === null) return null
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-emerald-700/60 bg-slate-800 p-8 shadow-xl">
          <h1
            ref={confirmationTitleRef}
            tabIndex={-1}
            className="text-3xl font-bold text-white tracking-tight focus:outline-none"
          >
            Registration Successful
          </h1>
          <div
            role="status"
            aria-atomic="true"
            className="mt-5 rounded-lg border border-emerald-900/50 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400"
          >
            <p>
              {registrationType === 'student'
                ? 'Your student account has been created.'
                : `Your ${registrationType} registration has been submitted.`}
            </p>
            <p className="mt-1 font-semibold">Awaiting institutional approval</p>
          </div>
          <p className="mt-4 text-sm text-slate-300 leading-relaxed">
            Your registration has been submitted to{' '}
            <span className="font-semibold text-white">{resolvedInstitution?.name ?? success.institution_code}</span>.
          </p>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            {registrationType === 'student'
              ? 'An institution administrator or authorized staff member will review your student account.'
              : 'Your institution administrator will review your registration.'}{' '}
            You can sign in after your account has been approved.
          </p>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            If you receive a confirmation email, use its link to verify your email address. Email verification is
            separate from institutional approval.
          </p>
          {registrationType === 'student' && (
            <p className="mt-2 text-sm text-slate-300 leading-relaxed">
              After approval, return to login with your email, register number, or university roll number. Your
              institution code is <span className="font-semibold text-white">{success.institution_code}</span>.
            </p>
          )}
          <p className="mt-2 text-sm text-slate-400 leading-relaxed">
            For questions about your registration, contact your institution administrator.
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

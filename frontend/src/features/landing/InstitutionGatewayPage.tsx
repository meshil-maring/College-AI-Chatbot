import { useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  lookupInstitution,
  RegistrationError,
  registrationErrorMessage,
} from '../../services/registration/registration.ts'
import type { InstitutionLookupResponse } from '../../types/registration.ts'
import { createInstitutionBranding } from './institutionBranding.ts'

export default function InstitutionGatewayPage({ institutionCode }: { institutionCode: string }) {
  const query = useApiQuery<InstitutionLookupResponse>(['public', 'institution-lookup', institutionCode], () =>
    lookupInstitution(institutionCode),
  )
  const institution = query.data ?? null
  const failed = query.isError

  if (failed) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-center text-content">
        <section className="max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
          <h1 className="font-bold text-content text-page">Institution unavailable</h1>
          <p role="alert" className="mt-3 text-sm leading-6 text-muted">
            {query.error instanceof RegistrationError
              ? registrationErrorMessage(query.error)
              : 'We could not load that institution. Check the code or try again later.'}
          </p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="mt-6 mr-3 rounded-lg border border-control px-4 py-2 text-sm font-semibold text-content focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
          >
            {query.isFetching ? 'Retrying…' : 'Try again'}
          </button>
          <a
            href="/u"
            className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Choose another institution
          </a>
        </section>
      </main>
    )
  }

  if (institution === null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
        <p role="status" className="text-sm text-muted">
          Loading institution…
        </p>
      </main>
    )
  }

  const branding = createInstitutionBranding(institution)
  const code = institution.code.toLowerCase()

  return (
    <div className="min-h-screen bg-canvas text-content">
      <header className="border-b border-line bg-shell">
        <div className="ui-public-container flex min-h-17 items-center justify-between gap-4 py-4">
          <a
            href="/"
            className="rounded-md text-sm font-semibold text-muted hover:text-content focus:outline-none focus:ring-2 focus:ring-accent"
          >
            College AI Platform
          </a>
          <span className="rounded-full border border-accent bg-raised px-3 py-1 text-xs font-bold tracking-[0.18em] text-accent">
            DEMO
          </span>
        </div>
      </header>
      <main className="ui-public-container py-12 sm:py-16">
        <section
          className="rounded-xl border border-line bg-surface p-4 sm:p-6"
          style={{ borderTopColor: branding.primary_color }}
        >
          <div className="flex items-center gap-4">
            {branding.logo === null ? (
              <span
                aria-hidden="true"
                className="flex h-14 w-14 items-center justify-center rounded-xl bg-raised text-xl font-black text-accent"
              >
                {branding.name.slice(0, 2).toUpperCase()}
              </span>
            ) : (
              <img src={branding.logo} alt={`${branding.name} logo`} className="h-14 w-14 rounded-xl object-contain" />
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Institution gateway</p>
              <h1 className="mt-1 font-bold text-content text-page">{branding.name}</h1>
            </div>
          </div>
          <p className="mt-6 max-w-2xl text-base leading-7 text-muted">{branding.welcome_message}</p>

          <div className="mt-9 grid gap-5 md:grid-cols-2">
            <a
              href={`/u/${encodeURIComponent(code)}/ai`}
              className="rounded-xl border border-accent bg-raised p-6 hover:bg-raised focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <h2 className="font-bold text-content text-section">Public AI Chat</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                Ask about public university information. No sign-in is required.
              </p>
              <p className="mt-5 text-sm font-semibold text-accent">
                Open public AI <span aria-hidden="true">→</span>
              </p>
            </a>
            <a
              href={`/login/student?institution=${encodeURIComponent(institution.code)}`}
              className="rounded-xl border border-accent bg-raised p-6 hover:bg-raised focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <h2 className="font-bold text-content text-section">Student Login</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                Sign in for your profile, institution notices, learning resources, and AI chat.
              </p>
              <p className="mt-5 text-sm font-semibold text-accent">
                Continue securely <span aria-hidden="true">→</span>
              </p>
            </a>
          </div>
          <p className="mt-6 text-sm text-muted">
            New student?{' '}
            <a
              href={`/login/student?institution=${encodeURIComponent(institution.code)}&register=1`}
              className="rounded-sm font-semibold text-accent underline focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Register as Student
            </a>
          </p>
          <p className="mt-7 text-xs leading-5 text-muted">
            Public AI uses public knowledge only. Authentication and tenant access are resolved by the server after
            sign-in.
          </p>
        </section>
      </main>
    </div>
  )
}

import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { lookupInstitution } from '../../services/registration.ts'
import type { InstitutionLookupResponse } from '../../types/registration.ts'
import { createInstitutionBranding } from './institutionBranding.ts'

export default function InstitutionGatewayPage({ institutionCode }: { institutionCode: string }) {
  const query = useApiQuery<InstitutionLookupResponse>(
    ['public', 'institution-lookup', institutionCode],
    () => lookupInstitution(institutionCode),
  )
  const institution = query.data ?? null
  const failed = query.isError

  if (failed) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
        <section className="max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
          <h1 className="text-2xl font-bold text-white">Institution unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">We could not load that institution. Check the code or try again later.</p>
          <a href="/u" className="mt-6 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-300">Choose another institution</a>
        </section>
      </main>
    )
  }

  if (institution === null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
        <p role="status" className="text-sm text-slate-300">Loading institution…</p>
      </main>
    )
  }

  const branding = createInstitutionBranding(institution)
  const code = institution.code.toLowerCase()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-5">
          <a href="/" className="rounded-md text-sm font-semibold text-slate-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-300">College AI Platform</a>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold tracking-[0.18em] text-emerald-300">DEMO</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-8 py-16">
        <section className="rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-2xl" style={{ borderTopColor: branding.primary_color }}>
          <div className="flex items-center gap-4">
            {branding.logo === null ? (
              <span aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-xl font-black text-emerald-300">{branding.name.slice(0, 2).toUpperCase()}</span>
            ) : (
              <img src={branding.logo} alt={`${branding.name} logo`} className="h-14 w-14 rounded-2xl object-contain" />
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Institution gateway</p>
              <h1 className="mt-1 text-4xl font-bold text-white">{branding.name}</h1>
            </div>
          </div>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-300">{branding.welcome_message}</p>

          <div className="mt-9 grid gap-5 md:grid-cols-2">
            <a href={`/u/${encodeURIComponent(code)}/ai`} className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-6 hover:bg-emerald-500/15 focus:outline-none focus:ring-2 focus:ring-emerald-300">
              <h2 className="text-xl font-bold text-white">Public AI Chat</h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">Ask about public university information. No sign-in is required.</p>
              <p className="mt-5 text-sm font-semibold text-emerald-300">Open public AI <span aria-hidden="true">→</span></p>
            </a>
            <a href={`/login/student?institution=${encodeURIComponent(institution.code)}`} className="rounded-2xl border border-sky-500/40 bg-sky-500/10 p-6 hover:bg-sky-500/15 focus:outline-none focus:ring-2 focus:ring-sky-300">
              <h2 className="text-xl font-bold text-white">Student Login</h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">Sign in for student-authorized academic information and authenticated AI.</p>
              <p className="mt-5 text-sm font-semibold text-sky-300">Continue securely <span aria-hidden="true">→</span></p>
            </a>
          </div>
          <p className="mt-7 text-xs leading-5 text-slate-500">Public AI uses public knowledge only. Authentication and tenant access are resolved by the server after sign-in.</p>
        </section>
      </main>
    </div>
  )
}


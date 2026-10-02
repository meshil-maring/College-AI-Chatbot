import { useEffect, useRef, useState } from 'react'
import { FUTURE_CAPABILITIES, GATEWAY_ENTRIES, type GatewayEntry } from './landingConfig.ts'

function GatewayIcon({ role }: { role: GatewayEntry['role'] }) {
  const common = 'h-6 w-6'
  if (role === 'public') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={common}>
        <path d="M4 7.5h16M7.5 4v16M16.5 4v16M4 16.5h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    )
  }
  if (role === 'super_admin') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={common}>
        <path d="M12 3 4.5 6v5.2c0 4.7 3.2 8.2 7.5 9.8 4.3-1.6 7.5-5.1 7.5-9.8V6L12 3Z" stroke="currentColor" strokeWidth="1.6" />
        <path d="m9.2 12 1.8 1.8 3.9-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={common}>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5.5 20c.5-4 2.7-6 6.5-6s6 2 6.5 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function GatewayCard({ entry }: { entry: GatewayEntry }) {
  const platform = entry.area === 'platform'
  return (
    <a
      href={entry.href}
      data-role={entry.role}
      className={`group flex min-h-44 flex-col rounded-2xl border p-5 shadow-lg transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 ${
        platform
          ? 'border-violet-500/50 bg-violet-500/10 hover:border-violet-400 hover:bg-violet-500/15 focus:ring-violet-300'
          : 'border-slate-700 bg-slate-900/80 hover:-translate-y-0.5 hover:border-emerald-500/60 hover:bg-slate-800 focus:ring-emerald-300'
      }`}
    >
      <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${platform ? 'bg-violet-500/15 text-violet-300' : 'bg-emerald-500/10 text-emerald-300'}`}>
        <GatewayIcon role={entry.role} />
      </span>
      <h3 className="mt-5 text-lg font-semibold text-white">{entry.label}</h3>
      <p className="mt-2 flex-1 text-sm leading-6 text-slate-400">{entry.description}</p>
      <span className={`mt-4 text-sm font-semibold ${platform ? 'text-violet-300' : 'text-emerald-300'}`}>
        Continue <span aria-hidden="true">→</span>
      </span>
    </a>
  )
}

export default function LandingPage() {
  const [moreOpen, setMoreOpen] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const moreButtonRef = useRef<HTMLButtonElement>(null)
  const publicEntry = GATEWAY_ENTRIES.find((entry) => entry.role === 'public')!
  const institutionEntries = GATEWAY_ENTRIES.filter((entry) => entry.area === 'institution')
  const platformEntry = GATEWAY_ENTRIES.find((entry) => entry.role === 'super_admin')!

  useEffect(() => {
    if (moreOpen) closeButtonRef.current?.focus()
  }, [moreOpen])

  function closeMore(): void {
    setMoreOpen(false)
    window.setTimeout(() => moreButtonRef.current?.focus(), 0)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-5">
          <a href="/" aria-label="College AI home" className="flex items-center gap-3 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-300">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 text-sm font-black text-slate-950">CA</span>
            <span className="text-lg font-bold tracking-tight text-white">College AI</span>
          </a>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold tracking-[0.18em] text-emerald-300">DEMO</span>
        </div>
      </header>

      <main>
        <section className="border-b border-slate-800 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.13),transparent_38%)]">
          <div className="mx-auto max-w-7xl px-8 py-16">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">Multi-tenant university SaaS</p>
            <h1 className="mt-4 max-w-4xl text-5xl font-bold tracking-tight text-white">College AI Platform</h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
              One platform for students, faculty, staff, universities, and AI-powered academic assistance.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3 text-sm text-slate-400" aria-label="Platform hierarchy">
              <span className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2">Public knowledge</span>
              <span aria-hidden="true">+</span>
              <span className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2">Institution workspaces</span>
              <span aria-hidden="true">+</span>
              <span className="rounded-full border border-violet-500/40 bg-violet-500/10 px-4 py-2 text-violet-200">Platform administration</span>
            </div>
          </div>
        </section>

        <div className="mx-auto grid max-w-7xl gap-10 px-8 py-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <section aria-labelledby="public-access-heading">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Open access</p>
            <h2 id="public-access-heading" className="mt-2 text-2xl font-bold text-white">Public AI</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">No sign-in required. Choose an institution to ask questions against public knowledge only.</p>
            <div className="mt-5"><GatewayCard entry={publicEntry} /></div>
            <aside className="mt-5 rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm leading-6 text-slate-400">
              <strong className="text-slate-200">Privacy boundary:</strong> public AI cannot access student records or authenticated university information.
            </aside>
          </section>

          <section aria-labelledby="authenticated-access-heading">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">Secure access</p>
            <h2 id="authenticated-access-heading" className="mt-2 text-2xl font-bold text-white">Role-based workspaces</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">Every sign-in uses the shared authentication flow. Your server-verified role and institution determine the workspace you can access.</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {institutionEntries.map((entry) => <GatewayCard key={entry.role} entry={entry} />)}
              <GatewayCard entry={platformEntry} />
              <button
                ref={moreButtonRef}
                type="button"
                aria-haspopup="dialog"
                aria-expanded={moreOpen}
                onClick={() => setMoreOpen(true)}
                className="flex min-h-44 flex-col items-start justify-center rounded-2xl border border-dashed border-slate-600 bg-slate-900/30 p-5 text-left transition hover:border-slate-400 hover:bg-slate-900/60 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-slate-950"
              >
                <span className="text-3xl font-light text-slate-300" aria-hidden="true">+</span>
                <span className="mt-3 text-lg font-semibold text-white">Add more</span>
                <span className="mt-2 text-sm leading-6 text-slate-400">Preview future university services.</span>
              </button>
            </div>
          </section>
        </div>
      </main>

      <footer className="border-t border-slate-800 px-8 py-6 text-center text-xs text-slate-500">
        Demo gateway · Access is enforced by the platform backend, not this page.
      </footer>

      {moreOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="future-capabilities-heading"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 px-4"
          onKeyDown={(event) => {
            if (event.key === 'Escape') closeMore()
          }}
        >
          <section className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Platform roadmap</p>
                <h2 id="future-capabilities-heading" className="mt-2 text-2xl font-bold text-white">More university services</h2>
              </div>
              <button ref={closeButtonRef} type="button" onClick={closeMore} aria-label="Close future capabilities" className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-300">Close</button>
            </div>
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {FUTURE_CAPABILITIES.map((capability) => (
                <li key={capability} className="flex items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-950/60 px-4 py-3">
                  <span className="text-sm font-medium text-slate-200">{capability}</span>
                  <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Coming Soon</span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-xs leading-5 text-slate-500">These are roadmap previews only. No action or external service is connected in this demo.</p>
          </section>
        </div>
      ) : null}
    </div>
  )
}


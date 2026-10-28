import { useEffect, useRef, useState } from 'react'
import { Globe2, ShieldCheck, UserRound } from 'lucide-react'
import { FUTURE_CAPABILITIES, GATEWAY_ENTRIES, type GatewayEntry } from './landingConfig.ts'

function GatewayIcon({ role }: { role: GatewayEntry['role'] }) {
  const common = 'h-6 w-6'
  if (role === 'public') {
    return <Globe2 aria-hidden="true" className={common} strokeWidth={2} />
  }
  if (role === 'super_admin') {
    return <ShieldCheck aria-hidden="true" className={common} strokeWidth={2} />
  }
  return <UserRound aria-hidden="true" className={common} strokeWidth={2} />
}

function GatewayCard({ entry }: { entry: GatewayEntry }) {
  return (
    <a
      href={entry.href}
      data-role={entry.role}
      className="group flex min-h-44 flex-col rounded-xl border border-line bg-surface p-4 transition hover:border-accent hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
    >
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-ink">
        <GatewayIcon role={entry.role} />
      </span>
      <h3 className="mt-5 font-semibold text-content text-card">{entry.label}</h3>
      <p className="mt-2 flex-1 text-sm leading-6 text-muted">{entry.description}</p>
      <span className="mt-4 text-sm font-semibold text-accent">
        Continue <span aria-hidden="true">â†’</span>
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
    <div className="min-h-screen bg-canvas text-content">
      <header className="border-b border-line bg-shell">
        <div className="ui-public-container flex min-h-17 items-center justify-between gap-4 py-4">
          <a
            href="/"
            aria-label="College AI home"
            className="flex items-center gap-3 rounded-md focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-sm font-black text-ink">
              CA
            </span>
            <span className="text-lg font-bold tracking-tight text-content">College AI</span>
          </a>
          <span className="rounded-full border border-accent bg-raised px-3 py-1 text-xs font-bold tracking-[0.18em] text-accent">
            DEMO
          </span>
        </div>
      </header>

      <main>
        <section className="border-b border-line bg-canvas">
          <div className="ui-public-container py-12 sm:py-16">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-accent">Multi-tenant university SaaS</p>
            <h1 className="mt-4 max-w-4xl font-bold tracking-tight text-content text-page">College AI Platform</h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-muted">
              One platform for institution accounts, published information, and AI assistance.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3 text-sm text-muted" aria-label="Platform hierarchy">
              <span className="rounded-full border border-line bg-surface px-4 py-2">Public knowledge</span>
              <span aria-hidden="true">+</span>
              <span className="rounded-full border border-line bg-surface px-4 py-2">Institution workspaces</span>
              <span aria-hidden="true">+</span>
              <span className="rounded-full border border-accent bg-raised px-4 py-2 text-accent">
                Platform administration
              </span>
            </div>
            <div className="mt-8" role="group" aria-labelledby="register-heading">
              <h2 id="register-heading" className="font-semibold uppercase tracking-[0.18em] text-muted text-section">
                Register
              </h2>
              <div className="mt-3 flex flex-wrap gap-3">
                <a
                  href="/register/university"
                  className="rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-ink shadow-none hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Register your university
                </a>
                <a
                  href="/login/faculty?register=1"
                  className="rounded-lg border border-accent bg-raised px-5 py-3 text-sm font-semibold text-accent hover:border-accent hover:bg-raised focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Register as faculty
                </a>
                <a
                  href="/login/staff?register=1"
                  className="rounded-lg border border-warning bg-warning-bg px-5 py-3 text-sm font-semibold text-accent hover:border-accent hover:bg-warning-bg focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Register as staff
                </a>
                <a
                  href="/register/super-admin"
                  className="rounded-lg border border-accent bg-raised px-5 py-3 text-sm font-semibold text-accent hover:border-accent hover:bg-raised focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Register as Super Admin
                </a>
              </div>
            </div>
          </div>{' '}
        </section>

        <div className="ui-public-container grid gap-8 py-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <section aria-labelledby="public-access-heading">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Open access</p>
            <h2 id="public-access-heading" className="mt-2 font-bold text-content text-section">
              Public AI
            </h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted">
              No sign-in required. Choose an institution to ask questions against public knowledge only.
            </p>
            <div className="mt-5">
              <GatewayCard entry={publicEntry} />
            </div>
            <aside className="mt-5 rounded-xl border border-line bg-surface p-4 text-sm leading-6 text-muted">
              <strong className="text-content">Privacy boundary:</strong> public AI cannot access student records or
              authenticated university information.
            </aside>
          </section>

          <section aria-labelledby="authenticated-access-heading">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Secure access</p>
            <h2 id="authenticated-access-heading" className="mt-2 font-bold text-content text-section">
              Role-based workspaces
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Every sign-in uses the shared authentication flow. Your server-verified role and institution determine the
              workspace you can access.
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {institutionEntries.map((entry) => (
                <GatewayCard key={entry.role} entry={entry} />
              ))}
              <GatewayCard entry={platformEntry} />
              <button
                ref={moreButtonRef}
                type="button"
                aria-haspopup="dialog"
                aria-expanded={moreOpen}
                onClick={() => setMoreOpen(true)}
                className="flex min-h-44 flex-col items-start justify-center rounded-xl border border-dashed border-control bg-surface p-5 text-left transition hover:border-control hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950"
              >
                <span className="text-3xl font-light text-muted" aria-hidden="true">
                  +
                </span>
                <span className="mt-3 text-lg font-semibold text-content">Add more</span>
                <span className="mt-2 text-sm leading-6 text-muted">Preview future university services.</span>
              </button>
            </div>
          </section>
        </div>
      </main>

      <footer className="border-t border-line px-8 py-6 text-center text-xs text-muted">
        Demo gateway Â· Access is enforced by the platform backend, not this page.
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
          <section className="w-full max-w-xl rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Platform roadmap</p>
                <h2 id="future-capabilities-heading" className="mt-2 font-bold text-content text-section">
                  More university services
                </h2>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                onClick={closeMore}
                aria-label="Close future capabilities"
                className="rounded-lg border border-control px-3 py-2 text-sm text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
              >
                Close
              </button>
            </div>
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {FUTURE_CAPABILITIES.map((capability) => (
                <li
                  key={capability}
                  className="flex items-center justify-between gap-3 rounded-xl border border-line bg-canvas px-4 py-3"
                >
                  <span className="text-sm font-medium text-content">{capability}</span>
                  <span className="rounded-full bg-surface px-2 py-1 text-xs font-semibold uppercase tracking-wide text-muted">
                    Coming Soon
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-xs leading-5 text-muted">
              These are roadmap previews only. No action or external service is connected in this demo.
            </p>
          </section>
        </div>
      ) : null}
    </div>
  )
}

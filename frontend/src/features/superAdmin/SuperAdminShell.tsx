import { useEffect, useState } from 'react'
import { getPlatformIdentity } from '../../services/platformApi.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import InstitutionManagement from './InstitutionManagement.tsx'
import PlatformAuditView from './PlatformAuditView.tsx'

const PLATFORM_AREAS = [
  'University Admins',
  'Platform AI',
  'Usage',
  'Features',
  'Security',
  'Platform Settings',
] as const

type PlatformSection = 'institutions' | 'audit'

/**
 * Phase 7.14 platform shell.
 *
 * The Phase 7.12 authorization gate is UNCHANGED and still runs first: the
 * shell renders only after `GET /platform/me` returns an allow response. Phase
 * 7.14 adds the read-only Platform Audit section; every other platform area
 * stays an honest "Coming Soon" placeholder with no fake functionality.
 *
 * Rendering the shell is a UX affordance, never an authorization decision —
 * each backend endpoint independently enforces `require_super_admin`.
 */
export default function SuperAdminShell() {
  const { user, accessToken, logout } = useAuth()
  const [authorization, setAuthorization] = useState<'checking' | 'allowed' | 'denied'>('checking')
  const [section, setSection] = useState<PlatformSection>('institutions')

  useEffect(() => {
    let cancelled = false
    if (accessToken === null) {
      setAuthorization('denied')
      return () => { cancelled = true }
    }
    void getPlatformIdentity(accessToken).then(
      () => { if (!cancelled) setAuthorization('allowed') },
      () => { if (!cancelled) setAuthorization('denied') },
    )
    return () => { cancelled = true }
  }, [accessToken])

  if (authorization === 'checking') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
        <p>Verifying platform authorization…</p>
      </main>
    )
  }
  if (authorization === 'denied') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
        <section className="max-w-lg rounded-2xl border border-amber-900/50 bg-amber-500/10 p-10">
          <h1 className="text-2xl font-bold text-amber-300">Platform access restricted</h1>
          <p className="mt-4 text-slate-300">Your current session is not authorized for platform administration.</p>
          <button type="button" onClick={logout} className="mt-6 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white">Sign out</button>
        </section>
      </main>
    )
  }
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-violet-500/20 bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-8 py-5">
          <div>
            <p className="text-lg font-bold text-white">College AI</p>
            <p className="text-xs text-violet-300">Platform-level workspace · Demo</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-slate-400">{user?.email ?? 'Platform administrator'}</span>
            <button type="button" onClick={logout} className="rounded-lg border border-slate-600 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300">Sign out</button>
          </div>
        </div>
      </header>

      {/* Desktop-first 1280px+ layout: fixed platform sidebar + content area. */}
      <div className="mx-auto flex max-w-7xl gap-10 px-8 py-12">
        <nav aria-label="Platform sections" className="w-56 shrink-0">
          <ul className="space-y-1">
            <li>
              <button
                type="button"
                onClick={() => { setSection('institutions') }}
                aria-current={section === 'institutions' ? 'page' : undefined}
                className="block w-full rounded-lg bg-violet-500/15 px-4 py-2 text-left text-sm font-semibold text-violet-200"
              >
                Institutions
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => { setSection('audit') }}
                aria-current={section === 'audit' ? 'page' : undefined}
                className="block w-full rounded-lg bg-violet-500/15 px-4 py-2 text-left text-sm font-semibold text-violet-200"
              >
                Platform Audit
              </button>
            </li>
            {PLATFORM_AREAS.map((area) => (
              <li key={area}>
                <span className="flex items-center justify-between gap-2 rounded-lg px-4 py-2 text-sm text-slate-500">
                  {area}
                  <span className="rounded-full bg-slate-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                    Soon
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </nav>

        <main className="min-w-0 flex-1">
          {section === 'institutions' ? <InstitutionManagement /> : <PlatformAuditView />}
        </main>
      </div>
    </div>
  )
}


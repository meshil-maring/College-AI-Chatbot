/**
 * Phase 6.17 — Faculty dashboard.
 *
 * The dashboard renders ONLY information backed by an existing contract:
 *
 *   - Identity comes from the server-authoritative /auth/me response held in
 *     AuthProvider state (never re-derived client-side).
 *   - The workspace overview is the verified faculty capability map from
 *     `facultyNavigation.ts` (a UI mirror of the server authorization
 *     matrix) — no counts, statistics or percentages are invented.
 *   - The AI Assistant entry point opens the existing ChatShell, which is
 *     authorized for faculty by the existing backend chat contracts.
 *
 * State discipline: the shell only renders for an authenticated session whose
 * /auth/me identity has loaded, so no section can render a fabricated
 * "loading"/"0" state while a request is in flight; if the identity is
 * somehow missing a controlled neutral state is shown instead of partial
 * data. There are intentionally NO async data sections yet: no faculty
 * backend data contract exists to load (see the Phase 6.17 documentation).
 */

import type { CurrentUser } from '../../types/auth.ts'
import {
  FACULTY_WORKSPACE_SURFACES,
  type FacultyView,
} from './facultyNavigation.ts'
import FacultyIdentityCard from './FacultyIdentityCard.tsx'

export default function FacultyDashboard({
  user,
  onNavigate,
}: {
  user: CurrentUser
  onNavigate: (view: FacultyView) => void
}) {
  return (
    <div className="flex flex-col gap-6">
      <FacultyIdentityCard user={user} />

      <section
        aria-labelledby="faculty-workspace-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="faculty-workspace-heading" className="text-lg font-semibold text-white">
          Academic workspace
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Surfaces available to your faculty account. Access to additional
          academic areas is granted by your institution through the backend.
        </p>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FACULTY_WORKSPACE_SURFACES.map((surface) => (
            <li
              key={surface.key}
              className={`rounded-xl border p-4 ${
                surface.status === 'available'
                  ? 'border-emerald-700/60 bg-emerald-900/20'
                  : 'border-slate-700 bg-slate-800/60'
              }`}
            >
              <p className="text-sm font-semibold text-white">{surface.title}</p>
              <p className="mt-1 text-xs text-slate-300">{surface.description}</p>
              <p className="mt-2 text-xs font-medium">
                {surface.status === 'available' ? (
                  <span className="text-emerald-300">Available</span>
                ) : (
                  <span className="text-slate-400">Not available yet</span>
                )}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section
        aria-labelledby="faculty-assistant-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="faculty-assistant-heading" className="text-lg font-semibold text-white">
          Ask the AI Assistant
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Get answers about your institution using the existing chatbot.
        </p>
        <button
          type="button"
          onClick={() => onNavigate('assistant')}
          className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Open AI Assistant
        </button>
      </section>
    </div>
  )
}

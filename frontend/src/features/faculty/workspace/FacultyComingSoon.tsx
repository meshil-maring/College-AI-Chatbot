/**
 * Inert "Coming Soon" placeholder for faculty sections that have NO backend
 * contract today (Students, Attendance, Results, Notices, Learning
 * Resources — see the Phase 7.24 capabilities audit).
 *
 * Honesty rules, matching the SuperAdmin/Landing "Coming Soon" pattern:
 *
 *   - ZERO network requests — the component performs no API call on mount
 *     or render, so no loading, error or empty-data state can be faked.
 *   - ZERO invented content — no counts, names, rows, percentages or
 *     placeholder "sample" data of any kind.
 *   - ZERO actions — no buttons, forms, filters or links beyond the shell
 *     navigation itself.
 *   - The badge is a roadmap label, never a promise of a delivery date.
 *
 * The page `h1` comes from the shell (`FACULTY_VIEW_HEADINGS[view]`); this
 * component renders the section body only, reusing the verified workspace
 * description so the dashboard card and the section page never disagree.
 */

import {
  FACULTY_WORKSPACE_SURFACES,
  type FacultyView,
} from './facultyNavigation.ts'

export default function FacultyComingSoon({ view }: { view: FacultyView }) {
  const surface = FACULTY_WORKSPACE_SURFACES.find((item) => item.key === view)

  return (
    <section
      aria-label="Coming soon"
      className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
    >
      <span className="inline-block rounded-full bg-slate-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        Coming Soon
      </span>
      <p className="mt-4 text-sm font-medium text-white">
        No information is available for this section yet.
      </p>
      <p className="mt-2 text-sm text-slate-300">
        {surface?.description ??
          'This section is not available for faculty accounts yet.'}
      </p>
      <p className="mt-3 text-xs text-slate-400">
        Nothing on this page is loaded or simulated. When your institution
        enables this area, real data and actions will appear here.
      </p>
    </section>
  )
}
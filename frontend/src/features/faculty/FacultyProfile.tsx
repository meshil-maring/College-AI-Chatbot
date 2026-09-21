/**
 * Phase 6.17 — Faculty profile page.
 *
 * Renders the safe faculty identity (see FacultyIdentityCard) plus an
 * explicit, honest statement about which academic context fields the backend
 * provides today. No internal identifiers, no invented academic data.
 */

import type { CurrentUser } from '../../types/auth.ts'
import FacultyIdentityCard from './FacultyIdentityCard.tsx'

export default function FacultyProfile({ user }: { user: CurrentUser }) {
  return (
    <div className="flex flex-col gap-6">
      <FacultyIdentityCard user={user} />
      <section
        aria-labelledby="faculty-profile-context-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="faculty-profile-context-heading" className="text-lg font-semibold text-white">
          Academic context
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          Your institution has not linked academic context (department,
          program, or assigned subjects) to faculty accounts yet. When your
          institution provides it, it will appear here.
        </p>
      </section>
    </div>
  )
}

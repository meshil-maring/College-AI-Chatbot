/**
 * Phase 6.17 — Faculty profile page.
 *
 * Renders the safe faculty identity (see FacultyIdentityCard) plus an
 * explicit, honest statement about which academic context fields the backend
 * provides today. No internal identifiers, no invented academic data.
 */

import type { CurrentUser } from '../../types/auth.ts'
import FacultyIdentityCard from './FacultyIdentityCard.tsx'
import type { FacultyContext } from '../../types/faculty.ts'
import { validityLabel, visibleResponsibilities } from './responsibilities.ts'

export default function FacultyProfile({ user, context = user.faculty_context }: { user: CurrentUser; context?: FacultyContext | null }) {
  return (
    <div className="flex flex-col gap-6">
      <FacultyIdentityCard user={user} />
      <section
        aria-labelledby="faculty-profile-context-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="faculty-profile-context-heading" className="text-lg font-semibold text-white">
            Academic context
          </h2>
        </div>
        {context ? <>
          <h3 className="mt-4 font-semibold">Responsibilities</h3>
          <ul className="mt-2 space-y-3">{visibleResponsibilities(context).map((row) => <li key={row.responsibility_id}><p>{row.name} — {row.scope_label}</p><p className="text-sm text-slate-400">{validityLabel(row)}</p></li>)}</ul>
          {visibleResponsibilities(context).length === 0 ? <p className="mt-2 text-sm text-slate-400">No active responsibilities.</p> : null}
          <h3 className="mt-5 font-semibold">Teaching Assignments</h3>
          <ul className="mt-2 space-y-3">{context.teaching_assignments.filter((row) => row.is_active && Date.parse(row.start_at) <= Date.now() && (!row.end_at || Date.now() < Date.parse(row.end_at))).map((row) => <li key={row.assignment_id}><p>{row.section.course.name} — {row.section.program?.name} · {row.section.semester?.name} · Section {row.section.code}</p>{row.section.department ? <p className="text-sm text-slate-300">Department: {row.section.department.name}</p> : null}<p className="text-sm text-slate-400">{validityLabel(row)}</p></li>)}</ul>
          {context.teaching_assignments.length === 0 ? <p className="mt-2 text-sm text-slate-400">No active teaching assignments.</p> : null}
        </> : <p className="mt-2 text-sm text-slate-300">Academic assignments could not be loaded. Refresh your session to retry.</p>}
      </section>
    </div>
  )
}

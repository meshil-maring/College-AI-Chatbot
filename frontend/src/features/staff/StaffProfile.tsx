/**
 * Phase 6.18 — Staff profile page.
 *
 * Renders the safe staff identity (see StaffIdentityCard) plus an explicit,
 * honest statement about which profile fields the backend provides today.
 * No internal identifiers, no invented staff data (no employee ID, no
 * department, no designation — none of those models exist).
 */

import type { CurrentUser } from '../../types/auth.ts'
import StaffIdentityCard from './StaffIdentityCard.tsx'

export default function StaffProfile({ user }: { user: CurrentUser }) {
  return (
    <div className="flex flex-col gap-6">
      <StaffIdentityCard user={user} />
      <section
        aria-labelledby="staff-profile-context-heading"
        className="rounded-xl border border-line bg-surface p-6 shadow-none"
      >
        <h2 id="staff-profile-context-heading" className="font-semibold text-content text-section">
          Profile details
        </h2>
        <p className="mt-2 text-sm text-muted">
          Your institution has not linked additional profile details (department, designation, or assignment
          information) to staff accounts yet. When your institution provides them, they will appear here.
        </p>
      </section>
    </div>
  )
}

/**
 * Phase 6.19 — Admin profile page.
 *
 * Renders the safe admin identity (see AdminIdentityCard) plus an explicit,
 * honest statement about which profile fields the backend provides today.
 * No internal identifiers, no token material, no invented admin data (no
 * employee ID, no designation, no department, no phone number — none of
 * those models exist).
 */

import type { CurrentUser } from '../../../types/auth.ts'
import AdminIdentityCard from './AdminIdentityCard.tsx'

export default function AdminProfile({ user }: { user: CurrentUser }) {
  return (
    <div className="flex flex-col gap-6">
      <AdminIdentityCard user={user} />
      <section
        aria-labelledby="admin-profile-context-heading"
        className="rounded-xl border border-line bg-surface p-6 shadow-none"
      >
        <h2 id="admin-profile-context-heading" className="font-semibold text-content text-section">
          Profile details
        </h2>
        <p className="mt-2 text-sm text-muted">
          No additional profile details (designation, department, or contact information) are linked to administrator
          accounts yet. When the backend provides them, they will appear here.
        </p>
      </section>
    </div>
  )
}

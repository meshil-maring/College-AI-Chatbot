/**
 * Phase 6.19 — Admin profile page.
 *
 * Renders the safe admin identity (see AdminIdentityCard) plus an explicit,
 * honest statement about which profile fields the backend provides today.
 * No internal identifiers, no token material, no invented admin data (no
 * employee ID, no designation, no department, no phone number — none of
 * those models exist).
 */

import type { CurrentUser } from '../../types/auth.ts'
import AdminIdentityCard from './AdminIdentityCard.tsx'

export default function AdminProfile({ user }: { user: CurrentUser }) {
  return (
    <div className="flex flex-col gap-6">
      <AdminIdentityCard user={user} />
      <section
        aria-labelledby="admin-profile-context-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="admin-profile-context-heading" className="text-lg font-semibold text-white">
          Profile details
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          No additional profile details (designation, department, or contact
          information) are linked to administrator accounts yet. When the
          backend provides them, they will appear here.
        </p>
      </section>
    </div>
  )
}
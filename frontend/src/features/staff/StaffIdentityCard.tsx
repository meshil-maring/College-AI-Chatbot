/**
 * Phase 6.18 — Staff identity presentation.
 *
 * Renders ONLY safe fields the backend actually returns. The staff contract
 * today is `GET /api/v1/auth/me`, which provides:
 *
 *   - email            (safe, rendered)
 *   - role             (safe, rendered as "Staff")
 *   - institution_id   (INTERNAL tenant key — NEVER rendered)
 *   - user_id          (INTERNAL — NEVER rendered)
 *   - auth_user_id     (INTERNAL auth UUID — NEVER rendered)
 *
 * The backend has no staff profile model (no staffs table, no staff
 * identifier, department, designation or assignment association anywhere in
 * the Phase 6.18 audit), so none of those fields exist to render. Nothing
 * is invented.
 */

import type { CurrentUser } from '../../types/auth.ts'

export default function StaffIdentityCard({ user }: { user: CurrentUser }) {
  const email = user.email?.trim() || null

  return (
    <section
      aria-labelledby="staff-identity-heading"
      className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
    >
      <h2 id="staff-identity-heading" className="text-lg font-semibold text-white">
        Staff identity
      </h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Email</dt>
          <dd className="mt-1 break-words text-sm text-slate-100">{email ?? 'Not provided'}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Role</dt>
          <dd className="mt-1 text-sm text-slate-100">Staff</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Institution</dt>
          <dd className="mt-1 text-sm text-slate-100">
            {user.institution_id ? 'Linked to your institution' : 'No institution linked'}
          </dd>
        </div>
      </dl>
    </section>
  )
}

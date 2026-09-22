/**
 * Phase 6.19 — Admin identity presentation.
 *
 * Renders ONLY safe fields the backend actually returns. The admin identity
 * contract today is `GET /api/v1/auth/me` (held in AuthProvider state), which
 * provides:
 *
 *   - email            (safe, rendered)
 *   - role             (safe, rendered as "Admin")
 *   - institution_id   (INTERNAL tenant key — NEVER rendered; presence is
 *                        shown as "Linked to your institution")
 *   - user_id          (INTERNAL — NEVER rendered)
 *   - auth_user_id     (INTERNAL auth UUID — NEVER rendered)
 *
 * No JWT, no access token, no password, and no invented profile fields
 * (employee ID, designation, department, phone number — none of those models
 * exist for admin accounts) are ever rendered.
 */

import type { CurrentUser } from '../../types/auth.ts'

export default function AdminIdentityCard({ user }: { user: CurrentUser }) {
  const email = user.email?.trim() || null

  return (
    <section
      aria-labelledby="admin-identity-heading"
      className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
    >
      <h2 id="admin-identity-heading" className="text-lg font-semibold text-white">
        Administrator identity
      </h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Email</dt>
          <dd className="mt-1 break-words text-sm text-slate-100">{email ?? 'Not provided'}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Role</dt>
          <dd className="mt-1 text-sm text-slate-100">Admin</dd>
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
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

import type { CurrentUser } from '../../../types/auth.ts'

export default function AdminIdentityCard({ user }: { user: CurrentUser }) {
  const email = user.email?.trim() || null

  return (
    <section
      aria-labelledby="admin-identity-heading"
      className="rounded-xl border border-line bg-surface p-6 shadow-none"
    >
      <h2 id="admin-identity-heading" className="font-semibold text-content text-section">
        Administrator identity
      </h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">Email</dt>
          <dd className="mt-1 break-words text-sm text-content">{email ?? 'Not provided'}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">Role</dt>
          <dd className="mt-1 text-sm text-content">Admin</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">Institution</dt>
          <dd className="mt-1 text-sm text-content">
            {user.institution_id ? 'Linked to your institution' : 'No institution linked'}
          </dd>
        </div>
      </dl>
    </section>
  )
}

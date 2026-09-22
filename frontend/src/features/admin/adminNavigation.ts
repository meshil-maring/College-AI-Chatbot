/**
 * Phase 6.19 — Admin navigation model.
 *
 * The admin experience has ONE navigation definition, derived exclusively
 * from the server-authoritative role held in AuthProvider state
 * (`/auth/me` -> `user.role`, Phase 6.15.4). The shell previously inlined
 * this list; it now mirrors the staff/faculty/student navigation-model
 * pattern so the fail-closed behaviour is testable without rendering.
 *
 * UX ONLY — NEVER AUTHORIZATION:
 * This module decides which links to RENDER. It is not a security boundary.
 * Every navigation target calls a backend endpoint that re-resolves the
 * caller's identity server-side from the JWT, and every /admin/* surface
 * stays behind `require_roles("admin", ...)` (the Phase 6.4 approval queue
 * additionally authorizes staff with the tenant-pinned `_approval_scope`).
 * Removing or editing this file cannot grant access to anything: a user who
 * manually requests an admin URL still receives 403 FORBIDDEN from the
 * backend unless the server resolves the `admin` role for their account.
 *
 * Every visible navigation item maps to a server-verified backend contract:
 *
 *   dashboard      -> GET  /admin/dashboard                    (require_roles("admin"))
 *   approvals      -> GET  /admin/students/pending             (require_roles("admin","staff"))
 *                     POST /admin/students/{id}/approve|reject
 *   students       -> GET  /admin/students (+ CRUD)            (require_roles("admin"))
 *   attendance     -> GET/POST/PATCH/DELETE /admin/attendance* (require_roles("admin"))
 *   results        -> GET/POST/PATCH/DELETE /admin/results*,
 *                     POST /admin/results/csv-upload           (require_roles("admin"))
 *   test-results   -> GET/POST/PATCH/DELETE /admin/test-results* (require_roles("admin"))
 *   notices        -> CRUD /admin/notices*                     (require_roles("admin"))
 *   documents      -> CRUD /admin/knowledge-sources*,
 *                     /admin/documents* (+ /documents pipeline) (require_roles("admin"))
 *   faqs           -> CRUD /admin/faqs*                        (require_roles("admin"))
 *   assistant      -> GET /conversations, POST /generation/chat (get_current_user)
 *   profile        -> GET /auth/me identity already in AuthProvider state
 *
 * No speculative surfaces (no user management, no role management, no
 * institution administration links — those exist in the backend for admins
 * but have NO frontend manager today, so no navigation entry is added).
 */

/** The only role that renders the admin shell (App.tsx gates on this too). */
const ADMIN_SHELL_ROLES: readonly string[] = ['admin']

/** Every view the admin shell can render (no router library is installed). */
export type AdminView =
  | 'dashboard'
  | 'approvals'
  | 'students'
  | 'attendance'
  | 'results'
  | 'test-results'
  | 'notices'
  | 'documents'
  | 'faqs'
  | 'assistant'
  | 'profile'

export interface AdminNavItem {
  readonly key: AdminView
  readonly label: string
}

/**
 * The admin navigation, in display order. Deliberately contains ONLY
 * server-verified admin capabilities.
 */
export const ADMIN_NAV_ITEMS: readonly AdminNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'approvals', label: 'Student Approvals' },
  { key: 'students', label: 'Students' },
  { key: 'attendance', label: 'Attendance' },
  { key: 'results', label: 'Results' },
  { key: 'test-results', label: 'Test Results' },
  { key: 'notices', label: 'Notices' },
  { key: 'documents', label: 'Documents' },
  { key: 'faqs', label: 'FAQs' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'profile', label: 'Profile' },
]

/**
 * Return the navigation for a server-resolved role.
 *
 * Only the admin role receives any navigation. Anything else (including
 * `null`/unknown values, and the staff/faculty/student roles that have their
 * own shells) receives an EMPTY navigation — the fail-safe behaviour,
 * consistent with shell selection in `App.tsx`, which never renders this
 * shell for those roles in the first place.
 */
export function buildAdminNavigation(role: string | null): readonly AdminNavItem[] {
  if (role === null) return []
  if (!ADMIN_SHELL_ROLES.includes(role)) return []
  return ADMIN_NAV_ITEMS
}

/** Human-readable heading for each view (used for the page `h1`). */
export const ADMIN_VIEW_HEADINGS: Readonly<Record<AdminView, string>> = {
  dashboard: 'Dashboard',
  approvals: 'Student Approvals',
  students: 'Students',
  attendance: 'Attendance',
  results: 'Results',
  'test-results': 'Test Results',
  notices: 'Notices',
  documents: 'Documents',
  faqs: 'FAQs',
  assistant: 'AI Assistant',
  profile: 'Profile',
}
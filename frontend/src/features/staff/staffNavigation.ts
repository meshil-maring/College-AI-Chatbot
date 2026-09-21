/**
 * Phase 6.18 — Staff navigation model.
 *
 * The staff experience has ONE navigation definition, derived exclusively
 * from the server-authoritative role held in AuthProvider state
 * (`/auth/me` -> `user.role`, Phase 6.15.4).
 *
 * UX ONLY — NEVER AUTHORIZATION:
 * This module decides which links to RENDER. It is not a security boundary.
 * The staff-facing backend capabilities that exist today are:
 *
 *   1. The authenticated chat surface (conversations + generation chat use
 *      the plain `get_current_user` dependency) -> "AI Assistant".
 *   2. The Phase 6.4 student approval queue (the ONLY /admin/* surface the
 *      backend authorizes for staff: `require_roles("admin", "staff")` on
 *      `GET /admin/students/pending`, `POST /admin/students/{id}/approve`
 *      and `POST /admin/students/{id}/reject`, with tenant-scoped
 *      `_approval_scope`) -> "Student Approvals".
 *
 * Every OTHER academic/administrative surface is verified server-side as
 * staff-DENIED and therefore has NO navigation entry:
 *
 *   - /students/me/*                    -> 404 STUDENT_PROFILE_NOT_FOUND
 *                                         (student-only identity chain)
 *   - /admin/students (CRUD), /admin/*attendance*, /admin/*results*,
 *     /admin/*test-results*, /admin/notices, /admin/faqs,
 *     /admin/knowledge-sources, /admin/documents, /admin/dashboard,
 *     /admin/me, /admin/audit-logs      -> 403 FORBIDDEN (admin-only)
 *   - user / role / institution management -> admin-only (403)
 *
 * The document ingestion pipeline (`/documents/*`) IS staff-authorized
 * (`require_roles("admin", "staff", "faculty")`), but — exactly as in the
 * Phase 6.17 faculty audit — there is NO staff-facing knowledge-source
 * listing contract to select an ingestion target, so NO upload UI is
 * rendered. Authorization to one pipeline stage is NOT inferred to be a
 * management surface.
 *
 * Removing or editing this file cannot grant access to anything: a staff
 * user who manually requests a student or admin URL still receives
 * 403/404 from the backend. The navigation contains NO administrative
 * surface (Admin Panel, User Management, Role Management, Institution
 * Management links do not exist in this list).
 */

/** The only role that renders the staff shell. */
const STAFF_SHELL_ROLES: readonly string[] = ['staff']

/** Every view the staff shell can render (no router library is installed). */
export type StaffView = 'dashboard' | 'approvals' | 'assistant' | 'profile'

export interface StaffNavItem {
  readonly key: StaffView
  readonly label: string
}

/**
 * The staff navigation, in display order. Deliberately contains ONLY
 * server-verified staff capabilities — no administrative entries and no
 * unverified operational surfaces.
 */
export const STAFF_NAV_ITEMS: readonly StaffNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'approvals', label: 'Student Approvals' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'profile', label: 'Profile' },
]

/**
 * Return the navigation for a server-resolved role.
 *
 * Only the staff role receives any navigation. Anything else (including
 * `null`/unknown values) receives an EMPTY navigation — the fail-safe
 * behaviour, consistent with shell selection in `App.tsx`, which never
 * renders this shell for those roles in the first place.
 */
export function buildStaffNavigation(role: string | null): readonly StaffNavItem[] {
  if (role === null) return []
  if (!STAFF_SHELL_ROLES.includes(role)) return []
  return STAFF_NAV_ITEMS
}

/** Human-readable heading for each view (used for the page `h1`). */
export const STAFF_VIEW_HEADINGS: Readonly<Record<StaffView, string>> = {
  dashboard: 'Dashboard',
  approvals: 'Student Approvals',
  assistant: 'AI Assistant',
  profile: 'Profile',
}

/**
 * Verified staff workspace surfaces, mirrored from the Phase 6.18 backend
 * authorization audit. `available` means a staff-authorized backend
 * contract EXISTS; `not-available` means the backend explicitly denies the
 * capability (or no usable staff contract exists yet). This is presentation
 * of the authorization matrix — NOT fabricated data: no counts,
 * percentages or statistics are ever rendered.
 */
export type WorkspaceSurfaceStatus = 'available' | 'not-available'

export interface StaffWorkspaceSurface {
  readonly key: string
  readonly title: string
  readonly status: WorkspaceSurfaceStatus
  /** Neutral, non-failure wording for unavailable surfaces. */
  readonly description: string
}

export const STAFF_WORKSPACE_SURFACES: readonly StaffWorkspaceSurface[] = [
  {
    key: 'approvals',
    title: 'Student Approvals',
    status: 'available',
    description: 'Review, approve or reject student registrations for your institution.',
  },
  {
    key: 'assistant',
    title: 'AI Assistant',
    status: 'available',
    description: 'Ask questions using your institution chatbot.',
  },
  {
    key: 'students',
    title: 'Student Management',
    status: 'not-available',
    description: 'Student records management is reserved for administrators.',
  },
  {
    key: 'attendance',
    title: 'Attendance',
    status: 'not-available',
    description: 'Attendance management is not available for staff accounts yet.',
  },
  {
    key: 'results',
    title: 'Results',
    status: 'not-available',
    description: 'Results management is not available for staff accounts yet.',
  },
  {
    key: 'test-results',
    title: 'Test Results',
    status: 'not-available',
    description: 'Test results management is not available for staff accounts yet.',
  },
  {
    key: 'notices',
    title: 'Notices',
    status: 'not-available',
    description: 'Notice management is not available for staff accounts yet.',
  },
  {
    key: 'resources',
    title: 'Learning Resources',
    status: 'not-available',
    description: 'Learning resources are not available for staff accounts yet.',
  },
  {
    key: 'documents',
    title: 'Documents',
    status: 'not-available',
    description: 'Document management is not available for staff accounts yet.',
  },
  {
    key: 'user-management',
    title: 'User Management',
    status: 'not-available',
    description: 'User management is reserved for administrators.',
  },
]


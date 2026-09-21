/**
 * Phase 6.17 — Faculty navigation model.
 *
 * The faculty experience has ONE navigation definition, derived exclusively
 * from the server-authoritative role held in AuthProvider state
 * (`/auth/me` -> `user.role`, Phase 6.15.4).
 *
 * UX ONLY — NEVER AUTHORIZATION:
 * This module decides which links to RENDER. It is not a security boundary.
 * The only faculty-facing backend capabilities that exist today are the
 * authenticated chat surface (conversations + generation chat, which use the
 * plain `get_current_user` dependency) and the document ingestion pipeline
 * (`require_roles("admin", "staff", "faculty")`, no faculty-facing listing
 * contract). Every other academic surface (students, attendance, results,
 * notices, learning resources) is verified server-side as faculty-DENIED:
 *
 *   - /students/me/*   -> 404 STUDENT_PROFILE_NOT_FOUND (student-only
 *                        identity chain; a faculty account has no students
 *                        row, so the endpoints fail closed)
 *   - /admin/*         -> 403 FORBIDDEN (require_roles("admin"); faculty is
 *                        NOT part of the admin/staff approval boundary)
 *
 * Because no faculty -> student scope (assignment/subject/department link)
 * exists in the backend, NO student list, attendance, results, notices or
 * resources navigation entry is rendered. Removing or editing this file
 * cannot grant access to anything: a faculty user who manually requests a
 * student or admin URL still receives 403/404 from the backend.
 *
 * The faculty navigation contains NO administrative surface. Admin, user
 * management, role management, and institution management links do not exist
 * in this list, so a faculty member can never be shown one by a
 * role-resolution mistake either.
 */

/** The only role that renders the faculty shell. */
const FACULTY_SHELL_ROLES: readonly string[] = ['faculty']

/** Every view the faculty shell can render (no router library is installed). */
export type FacultyView = 'dashboard' | 'assistant' | 'profile'

export interface FacultyNavItem {
  readonly key: FacultyView
  readonly label: string
}

/**
 * The faculty navigation, in display order. Deliberately contains ONLY
 * server-verified faculty capabilities — no student academic surfaces and no
 * administrative entries.
 */
export const FACULTY_NAV_ITEMS: readonly FacultyNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'profile', label: 'Profile' },
]

/**
 * Return the navigation for a server-resolved role.
 *
 * Only the faculty role receives any navigation. Anything else (including
 * `null`/unknown values) receives an EMPTY navigation — the fail-safe
 * behaviour, consistent with shell selection in `App.tsx`, which never
 * renders this shell for those roles in the first place.
 */
export function buildFacultyNavigation(role: string | null): readonly FacultyNavItem[] {
  if (role === null) return []
  if (!FACULTY_SHELL_ROLES.includes(role)) return []
  return FACULTY_NAV_ITEMS
}

/** Human-readable heading for each view (used for the page `h1`). */
export const FACULTY_VIEW_HEADINGS: Readonly<Record<FacultyView, string>> = {
  dashboard: 'Dashboard',
  assistant: 'AI Assistant',
  profile: 'Profile',
}

/**
 * Verified faculty workspace surfaces, mirrored from the Phase 6.17 backend
 * authorization audit. `available` means a faculty-authorized backend
 * contract EXISTS; `not-available` means the backend explicitly denies the
 * capability (or no faculty contract exists yet). This is presentation of the
 * authorization matrix — NOT fabricated data: no counts, percentages or
 * statistics are ever rendered.
 */
export type WorkspaceSurfaceStatus = 'available' | 'not-available'

export interface FacultyWorkspaceSurface {
  readonly key: string
  readonly title: string
  readonly status: WorkspaceSurfaceStatus
  /** Neutral, non-failure wording for unavailable surfaces. */
  readonly description: string
}

export const FACULTY_WORKSPACE_SURFACES: readonly FacultyWorkspaceSurface[] = [
  {
    key: 'assistant',
    title: 'AI Assistant',
    status: 'available',
    description: 'Ask questions using your institution chatbot.',
  },
  {
    key: 'students',
    title: 'Students',
    status: 'not-available',
    description: 'Student information is not available for faculty accounts yet.',
  },
  {
    key: 'attendance',
    title: 'Attendance',
    status: 'not-available',
    description: 'Attendance access is not available for faculty accounts yet.',
  },
  {
    key: 'results',
    title: 'Results',
    status: 'not-available',
    description: 'Results access is not available for faculty accounts yet.',
  },
  {
    key: 'notices',
    title: 'Notices',
    status: 'not-available',
    description: 'Institution notices are not available for faculty accounts yet.',
  },
  {
    key: 'resources',
    title: 'Learning Resources',
    status: 'not-available',
    description: 'Learning resources are not available for faculty accounts yet.',
  },
]

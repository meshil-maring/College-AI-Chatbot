/**
 * Phase 6.16 — Student navigation model.
 *
 * The student experience has ONE navigation definition, derived exclusively
 * from the server-authoritative role held in AuthProvider state
 * (`/auth/me` → `user.role`, Phase 6.15.4).
 *
 * UX ONLY — NEVER AUTHORIZATION:
 * This module decides which links to RENDER. It is not a security boundary.
 * Every navigation target calls a backend endpoint that re-resolves the
 * student's identity and tenant server-side from the JWT, and every privileged
 * route stays behind `require_roles(...)`. Removing or editing this file
 * cannot grant access to anything: a student who manually requests an admin
 * URL still receives 403 FORBIDDEN from the backend.
 *
 * The student navigation contains NO administrative surface. Admin, staff
 * management, student management, role management, and institution management
 * links do not exist in this list for any role, so a student can never be
 * shown one by a role-resolution mistake either.
 */

/** Roles that receive the student experience shell. */
const STUDENT_SHELL_ROLES: readonly string[] = ['student', 'staff', 'faculty']

/** Every view the student shell can render (no router library is installed). */
export type StudentView =
  | 'dashboard'
  | 'attendance'
  | 'results'
  | 'notices'
  | 'resources'
  | 'assistant'
  | 'profile'

export interface StudentNavItem {
  readonly key: StudentView
  readonly label: string
}

/**
 * The student navigation, in display order. Deliberately contains only the
 * authenticated student's own academic surfaces — no administrative entries.
 */
export const STUDENT_NAV_ITEMS: readonly StudentNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'attendance', label: 'Attendance' },
  { key: 'results', label: 'Results' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'profile', label: 'Profile' },
]

/**
 * Return the navigation for a server-resolved role.
 *
 * Only the three roles that render the student shell receive any navigation.
 * Anything else (including `null`/unknown values) receives an EMPTY navigation
 * — the fail-safe behaviour, consistent with `AuthenticatedShell`, which never
 * renders this shell for those roles in the first place.
 */
export function buildStudentNavigation(role: string | null): readonly StudentNavItem[] {
  if (role === null) return []
  if (!STUDENT_SHELL_ROLES.includes(role)) return []
  return STUDENT_NAV_ITEMS
}

/** Human-readable heading for each view (used for the page `h1`). */
export const STUDENT_VIEW_HEADINGS: Readonly<Record<StudentView, string>> = {
  dashboard: 'Dashboard',
  attendance: 'Attendance',
  results: 'Results',
  notices: 'Notices',
  resources: 'Learning Resources',
  assistant: 'AI Assistant',
  profile: 'Profile',
}

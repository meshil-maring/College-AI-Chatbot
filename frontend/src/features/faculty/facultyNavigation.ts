/** Faculty navigation reflects server permissions; resource authorization remains on the backend.
 * Results reuses the existing shell for tests, marks, publication and monitoring.
 */

import { hasPermission } from '../auth/permissions.ts'

/** The only role that renders the faculty shell. */
const FACULTY_SHELL_ROLES: readonly string[] = ['faculty']

/** Every view the faculty shell can render (no router library is installed). */
export type FacultyView =
  | 'dashboard'
  | 'assignments'
  | 'students'
  | 'attendance'
  | 'results'
  | 'notices'
  | 'resources'
  | 'assistant'
  | 'profile'
  | 'class-management'
  | 'department'

/**
 * Views with NO backend contract today: each renders the inert
 * `FacultyComingSoon` placeholder — no requests, no data, no actions.
 */
export const FACULTY_COMING_SOON_VIEWS: readonly FacultyView[] = [
  'students',
  'notices',
  'resources',
]

export interface FacultyNavItem {
  readonly key: FacultyView
  readonly label: string
}

/**
 * The faculty navigation, in display order. Contains the server-verified
 * faculty capabilities plus the inert "Coming Soon" placeholders — never an
 * administrative entry.
 */
export const FACULTY_NAV_ITEMS: readonly FacultyNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'assignments', label: 'My Sections' },
  { key: 'students', label: 'Students' },
  { key: 'attendance', label: 'Attendance' },
  { key: 'results', label: 'Results' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'profile', label: 'Profile' },
]

/**
 * Permission required to render each VERIFIED view. The "Coming Soon"
 * placeholders are deliberately absent: they expose no backend capability,
 * so they are keyed off the resolved faculty role only (the shell renders
 * them for any authenticated faculty identity).
 */
const FACULTY_VIEW_PERMISSIONS: Readonly<Partial<Record<FacultyView, string>>> = {
  dashboard: 'profile.own.read',
  assistant: 'ai.chat',
  profile: 'profile.own.read',
  assignments: 'faculty.assignments.read',
  attendance: 'attendance.read',
  results: 'results.read',
}

/**
 * Return the navigation for a server-resolved role.
 *
 * Only the faculty role receives any navigation. Anything else (including
 * `null`/unknown values) receives an EMPTY navigation — the fail-safe
 * behaviour, consistent with shell selection in `App.tsx`, which never
 * renders this shell for those roles in the first place.
 *
 * When `permissions` is provided, VERIFIED views are filtered by their
 * required capability; the inert "Coming Soon" placeholders are always kept
 * (no capability exists to check) — presentation only, never authorization.
 */
export function buildFacultyNavigation(
  role: string | null,
  permissions?: readonly string[],
  responsibilityGrants: readonly string[] = [],
): readonly FacultyNavItem[] {
  if (role === null) return []
  if (!FACULTY_SHELL_ROLES.includes(role)) return []
  const base = permissions === undefined ? FACULTY_NAV_ITEMS : FACULTY_NAV_ITEMS.filter((item) => {
    const required = FACULTY_VIEW_PERMISSIONS[item.key]
    if (required === undefined) return true // inert placeholder — no capability to check
    return hasPermission(permissions, required) || hasPermission(responsibilityGrants, required)
  })
  const additional: FacultyNavItem[] = []
  if (hasPermission(responsibilityGrants, 'academic.class.read')) additional.push({ key: 'class-management', label: 'Class Management' })
  if (hasPermission(responsibilityGrants, 'academic.department.read')) additional.push({ key: 'department', label: 'Department' })
  return [...base, ...additional]
}

/** Human-readable heading for each view (used for the page `h1`). */
export const FACULTY_VIEW_HEADINGS: Readonly<Record<FacultyView, string>> = {
  dashboard: 'Dashboard',
  assignments: 'My Sections',
  students: 'Students',
  attendance: 'Attendance',
  results: 'Results',
  notices: 'Notices',
  resources: 'Learning Resources',
  assistant: 'AI Assistant',
  profile: 'Profile',
  'class-management': 'Class Management',
  department: 'Department',
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
    key: 'assignments',
    title: 'My Sections',
    status: 'available',
    description: 'View active section assignments assigned to your account.',
  },
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
    status: 'available',
    description: 'Review assigned rosters, mark attendance, and validate imports.',
  },
  {
    key: 'results',
    title: 'Results',
    status: 'available',
    description: 'Manage authorized tests and review recorded marks and published results.',
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

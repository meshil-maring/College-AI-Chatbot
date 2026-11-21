import { hasPermission } from '../auth/access/permissions.ts'
import { hasResourceNavigation } from '../learning-resources/data/resourceIdentity.ts'

export type AdminView =
  'staff-faculty' | 'academic-setup' | 'approvals' | 'notices' | 'documents' | 'faqs' | 'assistant' | 'profile'
export type StudentWorkspacePage = 'register' | 'all' | 'bulk' | 'requests' | 'transfers' | 'new-transfer'
/** Sub-pages of Staff and Faculty Management, in sidebar order. */
export const STAFF_FACULTY_PAGES = ['requests', 'invitations', 'roster', 'permissions'] as const
export type StaffFacultyPage = (typeof STAFF_FACULTY_PAGES)[number]
export interface AdminNavItem {
  readonly key: AdminView
  readonly label: string
  /** Sidebar section heading. */
  readonly group: string
}
/** Sidebar order, grouped by task. Profile sits last, under Account. */
export const ADMIN_NAV_ITEMS: readonly AdminNavItem[] = [
  { key: 'academic-setup', label: 'Academic Setup', group: 'Academics' },
  { key: 'approvals', label: 'Students', group: 'People' },
  { key: 'staff-faculty', label: 'Staff and Faculty Management', group: 'People' },
  { key: 'notices', label: 'Notices', group: 'Communication' },
  { key: 'documents', label: 'Learning Resources', group: 'Communication' },
  { key: 'faqs', label: 'FAQs', group: 'Communication' },
  { key: 'assistant', label: 'AI Assistant', group: 'Assistant' },
  { key: 'profile', label: 'Profile', group: 'Account' },
]
/** Admin views with their own sub-pages in the sidebar. */
export const ADMIN_EXPANDABLE_VIEWS: readonly AdminView[] = ['academic-setup', 'approvals', 'staff-faculty']
const VIEW_PERMISSIONS: Record<AdminView, readonly string[]> = {
  profile: ['profile.own.read'],
  // The design overview is available to admins; catalogue access is checked separately.
  'academic-setup': [],
  'staff-faculty': ['users.read'],
  approvals: ['students.read'],
  notices: ['notices.read'],
  documents: ['documents.read'],
  faqs: ['ai.knowledge.read'],
  assistant: ['ai.chat'],
}
/** Navigation is presentation only. Endpoints enforce role, tenant and permissions. */
export function buildAdminNavigation(role: string | null, permissions?: readonly string[]): readonly AdminNavItem[] {
  if (role !== 'admin') return []
  return permissions === undefined
    ? ADMIN_NAV_ITEMS
    : ADMIN_NAV_ITEMS.filter((item) =>
        item.key === 'documents'
          ? hasResourceNavigation(role, permissions)
          : VIEW_PERMISSIONS[item.key].every((permission) => hasPermission(permissions, permission)),
      )
}
export const ADMIN_VIEW_HEADINGS: Record<AdminView, string> = {
  profile: 'Profile',
  'academic-setup': 'Academic Setup',
  'staff-faculty': 'Staff and Faculty Management',
  approvals: 'Students',
  notices: 'Notices',
  documents: 'Learning Resources',
  faqs: 'FAQs',
  assistant: 'AI Assistant',
}

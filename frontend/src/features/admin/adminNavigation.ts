import { hasPermission } from '../auth/access/permissions.ts'
import { hasResourceNavigation } from '../learning-resources/data/resourceIdentity.ts'

export type AdminView =
  | 'staff-faculty'
  | 'academic-setup'
  | 'approvals'
  | 'notices'
  | 'documents'
  | 'faqs'
  | 'assistant'
  | 'profile'
  | 'permissions'
export interface AdminNavItem {
  readonly key: AdminView
  readonly label: string
}
export const ADMIN_NAV_ITEMS: readonly AdminNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'academic-setup', label: 'Academic Setup' },
  { key: 'staff-faculty', label: 'Staff & Faculty' },
  { key: 'approvals', label: 'Student Approvals' },
  { key: 'notices', label: 'Notices' },
  { key: 'documents', label: 'Learning Resources' },
  { key: 'faqs', label: 'FAQs' },
  { key: 'assistant', label: 'AI Assistant' },
  { key: 'permissions', label: 'Staff Permissions' },
]
const VIEW_PERMISSIONS: Record<AdminView, readonly string[]> = {
  profile: ['profile.own.read'],
  // The design overview is available to admins; catalogue access is checked separately.
  'academic-setup': [],
  'staff-faculty': ['users.read'],
  approvals: ['students.read', 'students.approve', 'students.reject'],
  notices: ['notices.read'],
  documents: ['documents.read'],
  faqs: ['ai.knowledge.read'],
  assistant: ['ai.chat'],
  permissions: ['permissions.read'],
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
  'staff-faculty': 'Staff & Faculty',
  approvals: 'Student Approvals',
  notices: 'Notices',
  documents: 'Learning Resources',
  faqs: 'FAQs',
  assistant: 'AI Assistant',
  permissions: 'Staff Permissions',
}

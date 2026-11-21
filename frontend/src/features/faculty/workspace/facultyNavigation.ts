import { hasPermission } from '../../auth/access/permissions.ts'
import { hasResourceNavigation } from '../../learning-resources/data/resourceIdentity.ts'

export type FacultyView = 'profile' | 'notices' | 'resources' | 'transfers' | 'transfer-new' | 'assistant'
export interface FacultyNavItem {
  readonly key: FacultyView
  readonly label: string
}
export const FACULTY_NAV_ITEMS: readonly FacultyNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'transfers', label: 'Transfer Approvals' },
  { key: 'transfer-new', label: 'New Transfer' },
  { key: 'assistant', label: 'AI Assistant' },
]
export const FACULTY_COMING_SOON_VIEWS: readonly FacultyView[] = ['notices']
/**
 * HOD is an appointment, not a permission grant, so transfer approvals appear
 * only when the server reports that this faculty member may review transfers.
 */
export function buildFacultyNavigation(
  role: string | null,
  permissions?: readonly string[],
  canReviewTransfers = false,
): readonly FacultyNavItem[] {
  if (role !== 'faculty') return []
  const hodOnly = (key: FacultyView) => key === 'transfers' || key === 'transfer-new'
  const items = FACULTY_NAV_ITEMS.filter((item) => !hodOnly(item.key) || canReviewTransfers)
  if (permissions === undefined) return items
  return items.filter(
    (item) =>
      FACULTY_COMING_SOON_VIEWS.includes(item.key) ||
      hodOnly(item.key) ||
      (item.key === 'resources'
        ? hasResourceNavigation(role, permissions)
        : hasPermission(permissions, item.key === 'assistant' ? 'ai.chat' : 'profile.own.read')),
  )
}
export const FACULTY_VIEW_HEADINGS: Record<FacultyView, string> = {
  profile: 'Profile',
  notices: 'Notices',
  resources: 'Learning Resources',
  transfers: 'Transfer Approvals',
  'transfer-new': 'New Transfer',
  assistant: 'AI Assistant',
}
export type WorkspaceSurfaceStatus = 'available' | 'not-available'
export interface FacultyWorkspaceSurface {
  readonly key: string
  readonly title: string
  readonly status: WorkspaceSurfaceStatus
  readonly description: string
}
export const FACULTY_WORKSPACE_SURFACES: readonly FacultyWorkspaceSurface[] = [
  {
    key: 'notices',
    title: 'Notices',
    status: 'not-available',
    description: 'Institution notices are not available for faculty accounts yet.',
  },
  {
    key: 'resources',
    title: 'Learning Resources',
    status: 'available',
    description: 'Browse institution resources and submit your drafts for admin review.',
  },
]

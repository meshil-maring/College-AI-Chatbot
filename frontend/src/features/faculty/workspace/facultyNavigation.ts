import { hasPermission } from '../../auth/access/permissions.ts'
import { hasResourceNavigation } from '../../learning-resources/data/resourceIdentity.ts'

export type FacultyView = 'profile' | 'notices' | 'resources' | 'assistant'
export interface FacultyNavItem {
  readonly key: FacultyView
  readonly label: string
}
export const FACULTY_NAV_ITEMS: readonly FacultyNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
]
export const FACULTY_COMING_SOON_VIEWS: readonly FacultyView[] = ['notices']
export function buildFacultyNavigation(
  role: string | null,
  permissions?: readonly string[],
): readonly FacultyNavItem[] {
  if (role !== 'faculty') return []
  if (permissions === undefined) return FACULTY_NAV_ITEMS
  return FACULTY_NAV_ITEMS.filter(
    (item) =>
      FACULTY_COMING_SOON_VIEWS.includes(item.key) ||
      (item.key === 'resources'
        ? hasResourceNavigation(role, permissions)
        : hasPermission(permissions, item.key === 'assistant' ? 'ai.chat' : 'profile.own.read')),
  )
}
export const FACULTY_VIEW_HEADINGS: Record<FacultyView, string> = {
  profile: 'Profile',
  notices: 'Notices',
  resources: 'Learning Resources',
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

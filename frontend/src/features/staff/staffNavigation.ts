import { hasPermission } from '../auth/access/permissions.ts'
import { hasResourceNavigation } from '../learning-resources/data/resourceIdentity.ts'

export type StaffView = 'approvals' | 'assistant' | 'profile' | 'resources'
export interface StaffNavItem {
  readonly key: StaffView
  readonly label: string
}
export const STAFF_NAV_ITEMS: readonly StaffNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'approvals', label: 'Student Approvals' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
]
const VIEW_PERMISSIONS: Record<StaffView, string> = {
  profile: 'profile.own.read',
  approvals: 'students.approve',
  resources: 'documents.read',
  assistant: 'ai.chat',
}
export function buildStaffNavigation(role: string | null, permissions?: readonly string[]): readonly StaffNavItem[] {
  if (role !== 'staff') return []
  return permissions === undefined
    ? STAFF_NAV_ITEMS
    : STAFF_NAV_ITEMS.filter((item) =>
        item.key === 'resources'
          ? hasResourceNavigation(role, permissions)
          : hasPermission(permissions, VIEW_PERMISSIONS[item.key]),
      )
}
export const STAFF_VIEW_HEADINGS: Record<StaffView, string> = {
  profile: 'Profile',
  approvals: 'Student Approvals',
  resources: 'Learning Resources',
  assistant: 'AI Assistant',
}
export type WorkspaceSurfaceStatus = 'available' | 'not-available'
export interface StaffWorkspaceSurface {
  readonly key: string
  readonly title: string
  readonly status: WorkspaceSurfaceStatus
  readonly description: string
}
export const STAFF_WORKSPACE_SURFACES: readonly StaffWorkspaceSurface[] = [
  {
    key: 'resources',
    title: 'Learning Resources',
    status: 'available',
    description: 'Browse institution resources and submit your drafts for admin review.',
  },
  {
    key: 'approvals',
    title: 'Student Approvals',
    status: 'available',
    description: 'Review student account registrations for your institution.',
  },
  {
    key: 'assistant',
    title: 'AI Assistant',
    status: 'available',
    description: 'Ask questions using your institution chatbot.',
  },
]

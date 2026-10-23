import { hasPermission } from '../auth/access/permissions.ts'

export type StaffView = 'approvals' | 'assistant' | 'profile'
export interface StaffNavItem {
  readonly key: StaffView
  readonly label: string
}
export const STAFF_NAV_ITEMS: readonly StaffNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'approvals', label: 'Student Approvals' },
  { key: 'assistant', label: 'AI Assistant' },
]
const VIEW_PERMISSIONS: Record<StaffView, string> = {
  profile: 'profile.own.read',
  approvals: 'students.approve',
  assistant: 'ai.chat',
}
export function buildStaffNavigation(role: string | null, permissions?: readonly string[]): readonly StaffNavItem[] {
  if (role !== 'staff') return []
  return permissions === undefined
    ? STAFF_NAV_ITEMS
    : STAFF_NAV_ITEMS.filter((item) => hasPermission(permissions, VIEW_PERMISSIONS[item.key]))
}
export const STAFF_VIEW_HEADINGS: Record<StaffView, string> = {
  profile: 'Profile',
  approvals: 'Student Approvals',
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

import { hasPermission } from '../../auth/access/permissions.ts'

export type StudentView = 'profile' | 'notices' | 'resources' | 'assistant'
export interface StudentNavItem {
  readonly key: StudentView
  readonly label: string
}
export const STUDENT_NAV_ITEMS: readonly StudentNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
]
const PERMISSIONS: Record<StudentView, string> = {
  profile: 'profile.own.read',
  notices: 'notices.read',
  resources: 'documents.read',
  assistant: 'ai.chat',
}
export function buildStudentNavigation(
  role: string | null,
  permissions?: readonly string[],
): readonly StudentNavItem[] {
  if (!['student', 'staff', 'faculty'].includes(role ?? '')) return []
  return permissions === undefined
    ? STUDENT_NAV_ITEMS
    : STUDENT_NAV_ITEMS.filter((item) => hasPermission(permissions, PERMISSIONS[item.key]))
}
export const STUDENT_VIEW_HEADINGS: Record<StudentView, string> = {
  profile: 'Profile',
  notices: 'Notices',
  resources: 'Learning Resources',
  assistant: 'AI Assistant',
}

import { hasPermission } from '../../auth/access/permissions.ts'

export type StudentView = 'profile' | 'registration' | 'notices' | 'resources' | 'assistant'
export interface StudentNavItem {
  readonly key: StudentView
  readonly label: string
}
export const STUDENT_NAV_ITEMS: readonly StudentNavItem[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'registration', label: 'Semester Registration' },
  { key: 'notices', label: 'Notices' },
  { key: 'resources', label: 'Learning Resources' },
  { key: 'assistant', label: 'AI Assistant' },
]
const PERMISSIONS: Record<StudentView, string> = {
  profile: 'profile.own.read',
  registration: 'registration.own.read',
  notices: 'notices.read',
  resources: 'documents.read',
  assistant: 'ai.chat',
}
export function buildStudentNavigation(
  role: string | null,
  permissions?: readonly string[],
): readonly StudentNavItem[] {
  if (!['student', 'staff', 'faculty'].includes(role ?? '')) return []
  return STUDENT_NAV_ITEMS.filter(
    (item) =>
      (item.key !== 'registration' || role === 'student') &&
      (permissions === undefined || hasPermission(permissions, PERMISSIONS[item.key])),
  )
}
export const STUDENT_VIEW_HEADINGS: Record<StudentView, string> = {
  profile: 'Profile',
  registration: 'Semester Registration',
  notices: 'Notices',
  resources: 'Learning Resources',
  assistant: 'AI Assistant',
}

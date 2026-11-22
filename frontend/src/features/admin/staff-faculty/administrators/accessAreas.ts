import type { AdminAccessArea } from '../../../../types/admin/administrators.ts'

/** What each access area lets an administrator do. The server maps areas to permissions. */
export const ACCESS_AREAS: readonly { value: AdminAccessArea; label: string; description: string }[] = [
  {
    value: 'staff_faculty',
    label: 'Staff and Faculty',
    description: 'Members, invitations, roles, departments, responsibilities and teaching.',
  },
  {
    value: 'students',
    label: 'Students',
    description: 'Student accounts, approvals and transfers. Inviting students also needs Academic setup.',
  },
  {
    value: 'academic_setup',
    label: 'Academic setup',
    description: 'Departments, programs, courses, semesters and class sections.',
  },
  { value: 'content', label: 'Content', description: 'Notices, learning resources and FAQs.' },
  {
    value: 'staff_permissions',
    label: 'Staff permissions',
    description: 'Extra duties for Staff, limited to what this administrator can do.',
  },
  {
    value: 'settings_audit',
    label: 'Settings and audit',
    description: 'Institution settings and the audit log, including account history.',
  },
]

export const ALL_AREAS: AdminAccessArea[] = ACCESS_AREAS.map((area) => area.value)

/** Short summary of an administrator's access for lists. */
export function accessSummary(areas: readonly AdminAccessArea[] | null) {
  if (areas === null) return 'Full access'
  if (areas.length === 0) return 'Basics only (profile and assistant)'
  return ACCESS_AREAS.filter((area) => areas.includes(area.value))
    .map((area) => area.label)
    .join(', ')
}

/** Every area chosen means full access, stored as `null`. */
export function toAccess(areas: readonly AdminAccessArea[]): AdminAccessArea[] | null {
  return ALL_AREAS.every((area) => areas.includes(area)) ? null : [...areas]
}

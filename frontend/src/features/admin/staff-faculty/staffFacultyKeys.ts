import type { MembershipRole } from '../../../types/admin.ts'

export type RequestFilter = 'all' | MembershipRole | 'pending'

/**
 * Cache keys for Staff and Faculty Management, scoped to the signed-in session
 * token. Invalidating `all` refreshes every read on the page, including the
 * embedded Staff permissions section.
 */
export const staffFacultyKeys = {
  all: (token: string) => ['admin', 'staff-faculty', token] as const,
  requests: (token: string, filter: RequestFilter) => [...staffFacultyKeys.all(token), 'requests', filter] as const,
  roster: (token: string) => [...staffFacultyKeys.all(token), 'roster'] as const,
  invitations: (token: string) => [...staffFacultyKeys.all(token), 'invitations'] as const,
  departments: (token: string) => [...staffFacultyKeys.all(token), 'departments'] as const,
  heads: (token: string) => [...staffFacultyKeys.all(token), 'department-heads'] as const,
  responsibilities: (token: string) => [...staffFacultyKeys.all(token), 'responsibilities'] as const,
  responsibilityTargets: (token: string) => [...staffFacultyKeys.all(token), 'responsibility-targets'] as const,
  permissionMembers: (token: string) => [...staffFacultyKeys.all(token), 'permission-members'] as const,
  delegablePermissions: (token: string) => [...staffFacultyKeys.all(token), 'delegable-permissions'] as const,
  staffPermissions: (token: string, userId: string) =>
    [...staffFacultyKeys.all(token), 'staff-permissions', userId] as const,
}

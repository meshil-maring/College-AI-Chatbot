import type {
  MemberCommonProfile,
  MemberFacultyProfile,
  MemberProfileWrite,
  MemberStaffProfile,
  MembershipRole,
} from './memberships.ts'

export interface DepartmentRef {
  department_id: string
  code: string
  name: string
}

/** A member's employee profile; role sections are null until completed. */
export interface MemberProfileView {
  user_id: string
  role: MembershipRole
  common: MemberCommonProfile | null
  faculty: MemberFacultyProfile | null
  staff: MemberStaffProfile | null
  employment_status: 'active' | 'contract_ended' | 'not_set'
  primary_department: DepartmentRef | null
  additional_departments: DepartmentRef[]
}

export interface MemberProfileSaved {
  user_id: string
  role: MembershipRole
  message: string
}

export interface MemberAdditionalDepartmentsResult {
  user_id: string
  additional_departments: DepartmentRef[]
  message: string
}

export interface MemberHistoryEntry {
  audit_id: string
  action: string
  label: string
  actor_name: string
  performed_at: string
  details: Record<string, unknown>
}

export interface MemberHistory {
  user_id: string
  entries: MemberHistoryEntry[]
}

export type { MemberProfileWrite }

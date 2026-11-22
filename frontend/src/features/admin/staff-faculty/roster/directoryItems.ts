import type { Department } from '../../../../types/academicSetup.ts'
import type { MemberInvitation, MembershipRosterEntry } from '../../../../types/admin.ts'
import type { InstitutionAdmin } from '../../../../types/admin/administrators.ts'

export type UserType = 'faculty' | 'staff' | 'admin'

/**
 * One row of the user directory: a Staff/Faculty member, an administrator or a
 * pending invitation. Shared fields drive search and filters; the original
 * record decides how the row is shown and which actions it offers.
 */
export interface DirectoryItem {
  key: string
  name: string
  email: string
  userType: UserType
  /** Account status; 'invited' for an invitation that has not been accepted. */
  status: string
  departmentId: string | null
  departmentName: string | null
  employeeId: string | null
  designation: string | null
  employmentType: string | null
  employmentStatus: string
  member?: MembershipRosterEntry
  admin?: InstitutionAdmin
  invitation?: MemberInvitation
}

export function memberItem(member: MembershipRosterEntry): DirectoryItem {
  return {
    key: `member:${member.user_id}`,
    name: member.name || member.email,
    email: member.email,
    userType: member.role,
    status: member.status,
    departmentId: member.department_id,
    departmentName: member.department_name,
    employeeId: member.employee_id ?? null,
    designation: member.designation ?? null,
    employmentType: member.employment_type ?? null,
    employmentStatus: member.employment_status ?? 'not_set',
    member,
  }
}

/** Administrators hold no department or employee profile yet. */
export function adminItem(admin: InstitutionAdmin): DirectoryItem {
  return {
    key: `admin:${admin.user_id}`,
    name: admin.name || admin.email,
    email: admin.email,
    userType: 'admin',
    status: admin.status,
    departmentId: null,
    departmentName: null,
    employeeId: admin.profile?.employee_id ?? null,
    designation: admin.profile?.designation ?? (admin.is_owner ? 'Institution Owner' : 'Administrator'),
    employmentType: null,
    employmentStatus: 'not_set',
    admin,
  }
}

/** Only invitations still waiting count as "Invitation pending". */
export function invitationItem(invitation: MemberInvitation, departments: Department[]): DirectoryItem {
  return {
    key: `invitation:${invitation.invitation_id}`,
    name: invitation.full_name || invitation.email,
    email: invitation.email,
    userType: invitation.role,
    status: 'invited',
    departmentId: invitation.department_id,
    departmentName:
      departments.find((department) => department.department_id === invitation.department_id)?.name ?? null,
    employeeId: invitation.employee_id ?? null,
    designation: invitation.designation ?? null,
    employmentType: null,
    employmentStatus: 'not_set',
    invitation,
  }
}

/** Members, administrators who are not also members, and waiting invitations. */
export function buildDirectory(
  members: MembershipRosterEntry[],
  admins: InstitutionAdmin[],
  invitations: MemberInvitation[],
  departments: Department[],
): DirectoryItem[] {
  const memberIds = new Set(members.map((member) => member.user_id))
  return [
    ...members.map(memberItem),
    ...admins.filter((admin) => !memberIds.has(admin.user_id)).map(adminItem),
    ...invitations
      .filter((invitation) => invitation.status === 'invited')
      .map((invitation) => invitationItem(invitation, departments)),
  ]
}

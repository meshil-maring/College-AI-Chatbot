import type {
  MemberAdditionalDepartmentsResult,
  MemberHistory,
  MemberProfileSaved,
  MemberProfileView,
  MemberProfileWrite,
} from '../../types/admin/memberProfiles.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

const member = (userId: string) => `${ADMIN_BASE}/memberships/${encodeURIComponent(userId)}`

/** A Staff/Faculty member's employee profile and departments. */
export function getMemberProfile(accessToken: string, userId: string): Promise<MemberProfileView> {
  return requestJson<MemberProfileView>('GET', `${member(userId)}/profile`, accessToken)
}

/** Save the common profile and the member's role details. */
export function saveMemberProfile(
  accessToken: string,
  userId: string,
  profile: MemberProfileWrite,
): Promise<MemberProfileSaved> {
  return requestJson<MemberProfileSaved>('PUT', `${member(userId)}/profile`, accessToken, profile)
}

/** Replace the member's additional departments. */
export function setMemberAdditionalDepartments(
  accessToken: string,
  userId: string,
  departmentIds: string[],
): Promise<MemberAdditionalDepartmentsResult> {
  return requestJson<MemberAdditionalDepartmentsResult>(
    'PUT',
    `${member(userId)}/departments/additional`,
    accessToken,
    {
      department_ids: departmentIds,
    },
  )
}

/** Audit entries about one person in this institution, newest first. */
export function getMemberHistory(accessToken: string, userId: string): Promise<MemberHistory> {
  return requestJson<MemberHistory>('GET', `${member(userId)}/history`, accessToken)
}

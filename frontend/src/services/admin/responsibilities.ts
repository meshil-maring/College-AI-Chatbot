import type {
  MemberResponsibilityAssign,
  MemberResponsibilityList,
  MemberResponsibilityResult,
} from '../../types/admin/responsibilities.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

const BASE = `${ADMIN_BASE}/memberships/responsibilities`

/** Current and past Class In-Charge and Subject Coordinator appointments. */
export function listMemberResponsibilities(accessToken: string): Promise<MemberResponsibilityList> {
  return requestJson<MemberResponsibilityList>('GET', BASE, accessToken)
}

/** Appoint a Faculty member; hands over from the current holder if there is one. */
export function assignMemberResponsibility(
  accessToken: string,
  body: MemberResponsibilityAssign,
): Promise<MemberResponsibilityResult> {
  return requestJson<MemberResponsibilityResult>('POST', BASE, accessToken, body)
}

/** End an appointment now; it stays in the history. */
export function endMemberResponsibility(
  accessToken: string,
  responsibilityId: string,
): Promise<MemberResponsibilityResult> {
  return requestJson<MemberResponsibilityResult>(
    'POST',
    `${BASE}/${encodeURIComponent(responsibilityId)}/end`,
    accessToken,
  )
}

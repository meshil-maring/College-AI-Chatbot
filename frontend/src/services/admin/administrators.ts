import type { InstitutionAdminList, InstitutionAdminResult } from '../../types/admin/administrators.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

const BASE = `${ADMIN_BASE}/institution-admins`

/** Every administrator of the institution, the Owner and pending invitations. */
export function listInstitutionAdmins(accessToken: string): Promise<InstitutionAdminList> {
  return requestJson<InstitutionAdminList>('GET', BASE, accessToken)
}

/** Owner only: invite a new administrator by email. */
export function inviteInstitutionAdmin(
  accessToken: string,
  body: { email: string; full_name?: string | null },
): Promise<InstitutionAdminResult> {
  return requestJson<InstitutionAdminResult>('POST', `${BASE}/invitations`, accessToken, body)
}

/** Owner only: cancel a pending administrator invitation. */
export function cancelInstitutionAdminInvitation(
  accessToken: string,
  invitationId: string,
): Promise<InstitutionAdminResult> {
  return requestJson<InstitutionAdminResult>(
    'POST',
    `${BASE}/invitations/${encodeURIComponent(invitationId)}/cancel`,
    accessToken,
  )
}

/** Owner only: remove another administrator's access; the account stays. */
export function revokeInstitutionAdmin(accessToken: string, userId: string): Promise<InstitutionAdminResult> {
  return requestJson<InstitutionAdminResult>('DELETE', `${BASE}/${encodeURIComponent(userId)}`, accessToken)
}

/** Owner only: hand ownership to another active administrator. */
export function transferInstitutionOwnership(accessToken: string, userId: string): Promise<InstitutionAdminResult> {
  return requestJson<InstitutionAdminResult>('PUT', `${BASE}/owner`, accessToken, { user_id: userId })
}

import type {
  AuditLogEntry,
  MembershipDecisionResult,
  MembershipLifecycleResult,
  MembershipRequestList,
  MembershipRole,
  MembershipRoster,
} from '../../types/admin.ts'
import { ADMIN_BASE, requestJson } from './http.ts'
// ============================================================================
// Audit logs
// ============================================================================

export async function listAuditLogs(
  accessToken: string,
  limit = 50,
  tableName?: 'students' | 'student_registrations',
): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (tableName) params.set('table_name', tableName)
  return requestJson<AuditLogEntry[]>('GET', `${ADMIN_BASE}/audit-logs?${params}`, accessToken)
}

export interface StaffPermissionEntry {
  code: string
  inherited: boolean
  direct_grant_id: string | null
}

export interface StaffPermissionState {
  user_id: string
  institution_id: string
  permissions: StaffPermissionEntry[]
  delegable_permissions: string[]
}

export async function getDelegableStaffPermissions(accessToken: string): Promise<string[]> {
  const response = await requestJson<{ permissions: string[] }>(
    'GET',
    `${ADMIN_BASE}/permissions/delegable-staff`,
    accessToken,
  )
  return response.permissions
}

export function getStaffPermissions(accessToken: string, userId: string): Promise<StaffPermissionState> {
  return requestJson('GET', `${ADMIN_BASE}/staff/${encodeURIComponent(userId)}/permissions`, accessToken)
}

export function changeStaffPermissions(
  accessToken: string,
  userId: string,
  permissionCodes: string[],
  action: 'grant' | 'revoke',
): Promise<{ changed: number; permissions: StaffPermissionState }> {
  return requestJson(
    action === 'grant' ? 'POST' : 'DELETE',
    `${ADMIN_BASE}/staff/${encodeURIComponent(userId)}/permissions`,
    accessToken,
    { permission_codes: permissionCodes },
  )
}

// ============================================================================
// Staff / Faculty onboarding and roster (Phase 7.23)
// ============================================================================

export async function listMembershipRequests(
  accessToken: string,
  role?: MembershipRole,
  status?: string,
): Promise<MembershipRequestList> {
  const params = new URLSearchParams()
  if (role) params.set('role', role)
  if (status) params.set('status', status)
  const query = params.size ? `?${params.toString()}` : ''
  return requestJson<MembershipRequestList>('GET', `${ADMIN_BASE}/memberships/requests${query}`, accessToken)
}

export async function decideMembershipRequest(
  accessToken: string,
  requestId: string,
  decision: 'approve' | 'reject',
): Promise<MembershipDecisionResult> {
  return requestJson<MembershipDecisionResult>(
    'POST',
    `${ADMIN_BASE}/memberships/requests/${encodeURIComponent(requestId)}/${decision}`,
    accessToken,
    {},
  )
}

export async function listMembershipRoster(
  accessToken: string,
  role?: MembershipRole,
  status?: string,
): Promise<MembershipRoster> {
  const params = new URLSearchParams()
  if (role) params.set('role', role)
  if (status) params.set('status', status)
  const query = params.size ? `?${params.toString()}` : ''
  return requestJson<MembershipRoster>('GET', `${ADMIN_BASE}/memberships${query}`, accessToken)
}

export async function changeMembershipStatus(
  accessToken: string,
  userId: string,
  action: 'deactivate' | 'reactivate',
): Promise<MembershipLifecycleResult> {
  return requestJson<MembershipLifecycleResult>(
    'POST',
    `${ADMIN_BASE}/memberships/${encodeURIComponent(userId)}/${action}`,
    accessToken,
    {},
  )
}

export async function resendMembershipInvitation(accessToken: string, invitationId: string): Promise<unknown> {
  return requestJson<unknown>(
    'POST',
    `${ADMIN_BASE}/memberships/invitations/${encodeURIComponent(invitationId)}/resend`,
    accessToken,
    {},
  )
}

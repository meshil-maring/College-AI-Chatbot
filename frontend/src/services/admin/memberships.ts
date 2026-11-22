import type {
  AuditLogEntry,
  MemberDepartmentResult,
  MemberInvitationCancelled,
  MemberInvitationCreate,
  MemberInvitationCreated,
  MemberInvitationList,
  MemberRoleResult,
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

/**
 * Approve or reject a Staff/Faculty request. Approving a pending request needs
 * the department the administrator chose, and may approve the applicant as the
 * other member role.
 */
export async function decideMembershipRequest(
  accessToken: string,
  requestId: string,
  decision: 'approve' | 'reject',
  departmentId?: string,
  role?: MembershipRole,
): Promise<MembershipDecisionResult> {
  const body =
    decision === 'approve'
      ? { ...(departmentId ? { department_id: departmentId } : {}), ...(role ? { role } : {}) }
      : {}
  return requestJson<MembershipDecisionResult>(
    'POST',
    `${ADMIN_BASE}/memberships/requests/${encodeURIComponent(requestId)}/${decision}`,
    accessToken,
    body,
  )
}

/** Switch an approved member between Staff and Faculty. */
export async function setMemberRole(
  accessToken: string,
  userId: string,
  role: MembershipRole,
): Promise<MemberRoleResult> {
  return requestJson<MemberRoleResult>(
    'PUT',
    `${ADMIN_BASE}/memberships/${encodeURIComponent(userId)}/role`,
    accessToken,
    { role },
  )
}

/** Set or change the department of an existing Staff/Faculty member. */
export async function setMemberDepartment(
  accessToken: string,
  userId: string,
  departmentId: string,
): Promise<MemberDepartmentResult> {
  return requestJson<MemberDepartmentResult>(
    'PUT',
    `${ADMIN_BASE}/memberships/${encodeURIComponent(userId)}/department`,
    accessToken,
    { department_id: departmentId },
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
  action: 'deactivate' | 'reactivate' | 'suspend',
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

/** Staff/Faculty invitations still waiting for the person (or expired, to invite again). */
export function listMembershipInvitations(accessToken: string): Promise<MemberInvitationList> {
  return requestJson<MemberInvitationList>('GET', `${ADMIN_BASE}/memberships/invitations`, accessToken)
}

/** Invite a new Staff or Faculty member by email into the chosen department. */
export function createMembershipInvitation(
  accessToken: string,
  body: MemberInvitationCreate,
): Promise<MemberInvitationCreated> {
  return requestJson<MemberInvitationCreated>('POST', `${ADMIN_BASE}/memberships/invitations`, accessToken, body)
}

/** Cancel a pending invitation; its link stops working. */
export function cancelMembershipInvitation(
  accessToken: string,
  invitationId: string,
): Promise<MemberInvitationCancelled> {
  return requestJson<MemberInvitationCancelled>(
    'POST',
    `${ADMIN_BASE}/memberships/invitations/${encodeURIComponent(invitationId)}/cancel`,
    accessToken,
  )
}

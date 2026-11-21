// ============================================================================
// Audit log
// ============================================================================

export interface AuditLogEntry {
  audit_id: string
  actor_user_id: string
  action: string
  table_name: string | null
  record_id: string | null
  record_data: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  status: string
  performed_at: string
}

// ============================================================================
// Admin identity
// ============================================================================

export interface AdminIdentity {
  user_id: string
  auth_user_id: string
  email: string | null
  roles: string[]
  is_admin: boolean
}

// ============================================================================
// Staff / Faculty onboarding and roster (Phase 7.23)
// ============================================================================

export type MembershipRole = 'staff' | 'faculty'

export type MembershipRequestStatus = 'pending' | 'approved' | 'rejected'

export interface MembershipRequest {
  request_id: string
  full_name: string
  email: string
  requested_role: MembershipRole
  status: MembershipRequestStatus
  created_at: string
}

export interface MembershipRequestList {
  requests: MembershipRequest[]
  total: number
}

export interface MembershipDecisionResult {
  request_id: string
  status: 'approved' | 'rejected'
  already_applied: boolean
  message: string
}

export interface MembershipRosterEntry {
  user_id: string
  name: string
  email: string
  role: MembershipRole
  status: string
  created_at: string | null
  updated_at: string | null
  /** Department chosen by the administrator; null until one is set. */
  department_id: string | null
  department_code: string | null
  department_name: string | null
}

export interface MemberRoleResult {
  user_id: string
  role: MembershipRole
  already_applied: boolean
  message: string
}

export interface MemberDepartmentResult {
  user_id: string
  department_id: string
  department_code: string
  department_name: string
  message: string
}

export interface MembershipRoster {
  members: MembershipRosterEntry[]
  total: number
}

export interface MembershipLifecycleResult {
  user_id: string
  status: 'active' | 'deactivated'
  already_applied: boolean
  message: string
}

// ============================================================================
// Staff / Faculty invited by the administrator
// ============================================================================

export interface MemberInvitationCreate {
  email: string
  full_name: string
  role: MembershipRole
  department_id: string
}

export interface MemberInvitation {
  invitation_id: string
  email: string
  full_name: string | null
  role: MembershipRole
  department_id: string | null
  status: 'invited' | 'accepted' | 'cancelled' | 'expired'
  expires_at: string | null
  created_at: string | null
  email_delivery_status: string
  resend_count: number
  last_sent_at: string | null
}

export interface MemberInvitationList {
  invitations: MemberInvitation[]
  total: number
}

export interface MemberInvitationCreated {
  invitation: MemberInvitation
  email_delivery: { status: 'pending' | 'sent' | 'failed'; provider: string; detail?: string | null }
  expires_in_hours: number
  message: string
}

export interface MemberInvitationCancelled {
  invitation_id: string
  already_applied: boolean
  message: string
}

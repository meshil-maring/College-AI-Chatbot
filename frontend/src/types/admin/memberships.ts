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

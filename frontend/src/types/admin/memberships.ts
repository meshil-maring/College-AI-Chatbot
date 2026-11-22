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
  /** Employee profile summary; null until the administrator completes it. */
  employee_id?: string | null
  designation?: string | null
  employment_type?: string | null
  /** active, contract_ended or not_set (derived from the contract end date). */
  employment_status?: string
  additional_department_names?: string[]
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
  status: 'active' | 'suspended' | 'deactivated'
  already_applied: boolean
  message: string
}

// ============================================================================
// Staff / Faculty invited by the administrator
// ============================================================================

export type FacultyEmploymentType = 'permanent' | 'temporary' | 'contractual' | 'visiting' | 'guest'
export type StaffEmploymentType = 'permanent' | 'temporary' | 'contractual'
export type StaffCategory =
  | 'office_administration'
  | 'accounts_finance'
  | 'library'
  | 'it_support'
  | 'laboratory'
  | 'hostel_administration'
  | 'examination_office'
  | 'other'

/** Fields shared by every member type. Dates are ISO `YYYY-MM-DD`. */
export interface MemberCommonProfile {
  employee_id: string
  phone?: string | null
  designation: string
  joining_date: string
}

export interface MemberFacultyProfile {
  employment_type: FacultyEmploymentType
  employment_start_date: string
  /** Required unless employment is permanent. */
  contract_end_date?: string | null
  qualification?: string | null
  specialization?: string | null
  experience_years?: number | null
}

export interface MemberStaffProfile {
  staff_category: StaffCategory
  employment_type: StaffEmploymentType
  employment_start_date: string
  contract_end_date?: string | null
  responsibilities: string[]
}

/** The common profile plus exactly one role profile matching the member's role. */
export interface MemberProfileWrite {
  common: MemberCommonProfile
  faculty?: MemberFacultyProfile
  staff?: MemberStaffProfile
}

export interface MemberInvitationCreate {
  email: string
  full_name: string
  role: MembershipRole
  /** Primary department. */
  department_id: string
  profile: MemberProfileWrite
  additional_department_ids?: string[]
}

export interface MemberInvitation {
  invitation_id: string
  email: string
  full_name: string | null
  role: MembershipRole
  department_id: string | null
  employee_id?: string | null
  designation?: string | null
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

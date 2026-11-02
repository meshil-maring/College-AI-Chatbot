/** Account approval row; internal keys are used for decisions and never displayed. */
export interface PendingStudent {
  student_id: string
  user_id: string
  institution_id: string
  student_number: string
  email: string | null
  register_number: string | null
  university_roll_number: string | null
  approval_status: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StudentInvitationInput {
  student_name: string
  register_number: string
  university_roll_number: string | null
  email: string
}

export interface StudentInvitation extends StudentInvitationInput {
  invitation_id: string
  institution_id: string
  academic_section_id: string
  section_name: string | null
  section_code: string | null
  batch_name: string | null
  batch_code: string | null
  status: 'pending' | 'accepted' | 'cancelled'
  expires_at: string
  created_at: string
  email_delivery_status: 'pending' | 'sent' | 'failed'
  email_delivery_attempts: number
  resend_count: number
  last_sent_at: string | null
}

export interface StudentInvitationCreated {
  invitation: StudentInvitation
  delivery_status: 'sent' | 'failed'
  delivery_message: string
}

export interface StudentInvitationRowResult {
  row: number
  status: 'created' | 'failed' | 'duplicate'
  invitation: StudentInvitation | null
  delivery_status: 'sent' | 'failed' | null
  message: string
}

export interface StudentOnboardingBulkResult {
  row: number
  status: StudentInvitationRowResult['status']
  delivery_status: 'sent' | 'failed' | null
  message: string
}

export interface StudentInvitationBulkResult {
  total: number
  created: number
  failed: number
  rows: StudentInvitationRowResult[]
}

export interface StudentInvitationList {
  invitations: StudentInvitation[]
}

export interface StudentIdentityReviewRequest {
  email?: string | null
  register_number?: string | null
  university_roll_number?: string | null
}

export interface StudentIdentityAccountMatch {
  student_name: string
  email: string | null
  register_number: string | null
  university_roll_number: string | null
  approval_status: string
  account_status: string | null
  student_status: string
  is_active: boolean
  has_signed_in: boolean
  last_sign_in_at: string | null
  matches_email: boolean
  matches_register_number: boolean
  matches_university_roll_number: boolean
}

export interface StudentIdentityInvitationMatch {
  student_name: string
  email: string
  register_number: string
  university_roll_number: string | null
  status: 'pending'
  email_delivery_status: 'pending' | 'sent' | 'failed'
  expires_at: string
  last_sent_at: string | null
  has_signed_in: boolean
  matches_email: boolean
  matches_register_number: boolean
  matches_university_roll_number: boolean
}

export interface StudentIdentityReviewResponse {
  students: StudentIdentityAccountMatch[]
  invitations: StudentIdentityInvitationMatch[]
  email_conflict_exists: boolean
}

export type StudentDirectoryStatus = 'pending_sign_in' | 'signed_in' | 'no_signin'
export type StudentDirectoryFilter = 'all' | StudentDirectoryStatus

export interface StudentDirectoryRow {
  record_id: string
  record_type: 'student' | 'invitation'
  student_name: string
  email: string | null
  register_number: string | null
  university_roll_number: string | null
  status: StudentDirectoryStatus
  approval_status: string | null
  account_status: string | null
  student_status: string | null
  is_active: boolean | null
  last_sign_in_at: string | null
  email_delivery_status: 'pending' | 'sent' | 'failed' | null
  expires_at: string | null
  program_id: string | null
  program_name: string | null
  program_code: string | null
  course_name: string | null
  branch_name: string | null
  branch_code: string | null
  batch_name: string | null
  batch_code: string | null
  admission_cohort_id: string | null
  section_name: string | null
  section_code: string | null
  academic_section_id: string | null
  created_at: string
}

export interface StudentProfileUpdateInput {
  student_name: string
  register_number: string
  university_roll_number: string | null
  academic_section_id: string | null
}

export interface StudentInvitationUpdateInput extends Omit<StudentProfileUpdateInput, 'academic_section_id'> {
  email: string
  academic_section_id: string | null
}

export interface StudentInvitationUpdateResult {
  invitation: StudentInvitation
  email_changed: boolean
  delivery_status: 'sent' | 'failed' | null
  delivery_message: string | null
}

export type StudentDirectoryUpdateInput = StudentProfileUpdateInput | StudentInvitationUpdateInput

export interface StudentDirectoryProgram {
  program_id: string
  program_name: string
  program_code: string
}

export interface StudentDirectoryResponse {
  items: StudentDirectoryRow[]
  total: number
  limit: number
  offset: number
  summary: {
    total: number
    pending_sign_in: number
    signed_in: number
    no_signin: number
  }
  programs: StudentDirectoryProgram[]
}

/**
 * Student transfer and Head of Department contracts.
 *
 * Mirrors backend/app/api/academics/student_transfers.py. The server derives
 * the student, institution and current section; the browser only chooses a
 * target section and writes a reason.
 */

export type TransferType = 'section_transfer' | 'program_transfer'
export type TransferStatus = 'submitted' | 'under_review' | 'approved' | 'rejected' | 'cancelled'
export type TransferEventAction = 'submitted' | 'review_started' | 'approved' | 'rejected' | 'cancelled' | 'transferred'
export type TransferInitiator = 'student' | 'admin' | 'hod'
export type TransferDecisionAction = 'start_review' | 'approve' | 'reject'

export interface TransferSection {
  academic_section_id: string
  section_name: string
  section_code: string
  admission_cohort_id: string
  batch_name: string
  program_id: string
  program_name: string
  program_code: string
  department_id: string
  department_name: string
  program_semester_name: string
  semester_id: string
  term_name: string
  capacity: number | null
  seats_taken: number
}

export interface CurrentPlacement extends TransferSection {
  semester_registration_id: string
  registration_status: 'assigned' | 'registered'
  term_end_date: string
  term_open: boolean
}

export interface TransferOption extends TransferSection {
  transfer_type: TransferType
  has_seat: boolean
}

export interface TransferEvent {
  action: TransferEventAction
  comment: string | null
  created_at: string
}

export interface EnrolledSubjectSnapshot {
  name?: string
  code?: string
  credits?: number
}

export interface TransferRequest {
  transfer_request_id: string
  student_id: string
  student_name: string | null
  register_number: string | null
  transfer_type: TransferType
  status: TransferStatus
  reason: string
  initiated_by: TransferInitiator
  from_section: TransferSection | null
  to_section: TransferSection | null
  submitted_at: string
  review_started_at: string | null
  decided_at: string | null
  decided_as: 'admin' | 'hod' | null
  decision_comment: string | null
  cancelled_at: string | null
  previous_enrollments: EnrolledSubjectSnapshot[]
  events: TransferEvent[]
}

export interface StudentTransfers {
  institution_id: string
  current: CurrentPlacement | null
  options: TransferOption[]
  requests: TransferRequest[]
}

export interface TransferSubmit {
  to_section_id: string
  reason: string
}

export interface TransferCommandResult {
  transfer_request_id: string
  institution_id: string
  status: TransferStatus
}

export interface TransferReviews {
  institution_id: string
  can_review: boolean
  can_decide: boolean
  reviewer_role: 'admin' | 'hod' | null
  departments: { department_id: string; name: string }[]
  requests: TransferRequest[]
}

export interface DepartmentHead {
  department_id: string
  faculty_user_id: string
  name: string
  email: string | null
  assigned_at: string
  is_active_faculty: boolean
}

export interface FacultyCandidate {
  user_id: string
  name: string
  email: string | null
}

export interface DepartmentHeads {
  institution_id: string
  heads: DepartmentHead[]
  faculty: FacultyCandidate[]
}

/** A student an administrator or HOD may move directly (open term, in scope). */
export interface DirectTransferStudent {
  student_id: string
  student_name: string | null
  register_number: string | null
  current_section: TransferSection
  registration_status: 'assigned' | 'registered'
  has_open_request: boolean
}

export interface DirectTransferStudents {
  institution_id: string
  can_transfer: boolean
  actor_role: 'admin' | 'hod' | null
  students: DirectTransferStudent[]
}

export interface DirectTransferOptions {
  institution_id: string
  student_id: string
  actor_role: 'admin' | 'hod'
  current: TransferSection & { semester_registration_id: string; registration_status: 'assigned' | 'registered' }
  has_open_request: boolean
  options: TransferOption[]
}

export interface DirectTransferBody extends TransferSubmit {
  student_id: string
}

export interface DirectTransferResult extends TransferCommandResult {
  student_id: string
}

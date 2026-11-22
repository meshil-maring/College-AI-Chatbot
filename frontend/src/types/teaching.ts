/** Teaching assignments: which Faculty member teaches which subject offering. */
export type TeachingStatus = 'pending' | 'active' | 'rejected' | 'cancelled' | 'ended'

export interface TeachingOfferingLabel {
  academic_offering_id: string
  subject_code: string
  subject_name: string
  section_code: string
  section_name: string
  semester_name: string | null
  /** The department that owns the subject; its Head approves cross-department teaching. */
  department_id: string
  department_name: string
}

export interface TeachingAssignment extends TeachingOfferingLabel {
  assignment_id: string
  status: TeachingStatus
  needs_approval: boolean
  /** Active and its planned end date has not passed. */
  is_current: boolean
  faculty_user_id: string
  faculty_name: string
  starts_on: string
  planned_end_on: string | null
  requested_by_name: string | null
  requested_at: string
  decided_by_name: string | null
  decided_at: string | null
  decision_note: string | null
  ended_at: string | null
  /** The server says this viewer may approve or reject it now. */
  can_decide: boolean
  /** The server says this viewer may end it (or withdraw it while pending). */
  can_end: boolean
}

export interface TeachingAssignments {
  institution_id: string
  is_admin: boolean
  head_department_ids: string[]
  assignments: TeachingAssignment[]
}

export interface TeachingFacultyOption {
  user_id: string
  name: string
  /** Primary and additional departments. */
  department_ids: string[]
}

export interface TeachingOptions {
  institution_id: string
  offerings: TeachingOfferingLabel[]
  faculty: TeachingFacultyOption[]
}

export interface TeachingAssignmentCreate {
  academic_offering_id: string
  faculty_user_id: string
  starts_on: string | null
  planned_end_on: string | null
}

export interface TeachingCommandResult {
  assignment_id: string
  status: TeachingStatus
  already_applied: boolean
}

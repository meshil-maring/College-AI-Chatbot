/**
 * Class In-Charge and Subject Coordinator: dated responsibilities of a Faculty
 * member, like Head of Department. Dates are ISO `YYYY-MM-DD`.
 */
export type ResponsibilityKind = 'class_in_charge' | 'subject_coordinator'

export interface MemberResponsibility {
  responsibility_id: string
  responsibility: ResponsibilityKind
  faculty_user_id: string
  faculty_name: string
  /** Set for Class In-Charge. */
  academic_section_id: string | null
  /** Set for Subject Coordinator. */
  course_id: string | null
  target_code: string | null
  target_name: string | null
  starts_on: string
  planned_end_on: string | null
  ended_at: string | null
  /** Not ended and the planned end date has not passed. */
  is_current: boolean
}

export interface MemberResponsibilityList {
  responsibilities: MemberResponsibility[]
  total: number
}

export interface MemberResponsibilityAssign {
  faculty_user_id: string
  responsibility: ResponsibilityKind
  /** A class section for Class In-Charge, a catalogue course for Subject Coordinator. */
  target_id: string
  starts_on?: string | null
  planned_end_on?: string | null
}

export interface MemberResponsibilityResult {
  responsibility_id: string
  already_applied: boolean
  message: string
}

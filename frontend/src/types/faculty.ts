export interface AssignmentValidity {
  start_at: string
  end_at: string | null
  is_active: boolean
}

export interface AcademicSection {
  section_id: string
  name: string
  code: string
  department_id?: string
  program_id?: string
  semester_id?: string
  academic_year_id?: string
  course: { name: string; code: string }
  department?: { name: string; code: string }
  program?: { name: string }
  semester?: { name: string }
  academic_year?: { name: string }
}

export interface FacultyResponsibility extends AssignmentValidity {
  responsibility_id: string
  faculty_user_id: string
  responsibility_code: string
  name: string
  scope_type: string
  scope_id: string
  scope_label?: string
  state: string
  permissions: string[]
  effective_active: boolean
  revoked_at: string | null
  program_id?: string | null
}

export interface TeachingAssignment extends AssignmentValidity {
  assignment_id: string
  faculty_user_id: string
  section_id: string
  assigned_at: string
  section: AcademicSection
}

export interface FacultyContext {
  responsibilities: FacultyResponsibility[]
  teaching_assignments: TeachingAssignment[]
  responsibility_permissions: string[]
}

export interface ResponsibilityDefinition {
  code: string
  name: string
  allowed_scope_types: string[]
  exclusive_scope: boolean
  permissions: string[]
}

export interface ResponsibilityManagement {
  faculty: Array<{ id: string; first_name: string; last_name: string; email: string }>
  definitions: ResponsibilityDefinition[]
  departments: Array<{ department_id: string; name: string; code: string }>
  sections: AcademicSection[]
  responsibilities: FacultyResponsibility[]
}

export interface ResponsibilityPayload extends AssignmentValidity {
  scope_type: string
  scope_id: string
  program_id?: string | null
}

export interface AttendanceStudentSummary {
  roster_id: string
  section_id: string
  register_number: string
  student_name: string
  roster_status: string
  total_classes: number
  present_classes: number
  attendance_percentage: number | null
}

export interface ResponsibilityReport {
  responsibility: FacultyResponsibility
  sections: AcademicSection[]
  students: AttendanceStudentSummary[]
  low_attendance: AttendanceStudentSummary[]
  low_attendance_threshold: number
  faculty: Array<{ id: string; first_name: string; last_name: string }>
  session_count: number
}

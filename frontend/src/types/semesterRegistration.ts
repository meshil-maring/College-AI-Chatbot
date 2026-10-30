export interface SubjectOption {
  choice_option_id: string
  name: string
  curriculum_subject_ids: string[]
}
export interface ChoiceGroup {
  choice_group_id: string
  institution_id: string
  curriculum_version_id: string
  program_semester_id: string
  name: string
  options: SubjectOption[]
}
export interface ChoiceGroupDraft {
  curriculum_version_id: string
  program_semester_id: string
  name: string
  options: { name: string; curriculum_subject_ids: string[] }[]
}
export interface SemesterAssignment {
  semester_registration_id: string
  institution_id: string
  student_id: string
  academic_section_id: string
  semester_id: string
  status: 'assigned' | 'registered'
  selected_option_ids: string[]
  assigned_at: string
  registered_at: string | null
}
export interface RegistrationCatalogue {
  institution_id: string
  groups: ChoiceGroup[]
  students: { student_id: string; student_number: string; email: string | null; institution_id: string }[]
  assignments: SemesterAssignment[]
  can_manage_choices: boolean
  can_assign: boolean
}
export interface RegisteredSubject {
  course_id: string
  name: string
  code: string
  credits: number | null
}
export interface RegistrationSubject extends Omit<RegisteredSubject, 'course_id'> {
  curriculum_subject_id: string
  is_required: boolean
  academic_offering_id: string | null
  available: boolean
}
export interface StudentSemester extends SemesterAssignment {
  section_name: string
  batch_name: string
  program_name: string
  program_semester_name: string
  term_name: string
  start_date: string
  end_date: string
  groups: ChoiceGroup[]
  subjects: RegistrationSubject[]
  enrolled_subjects: RegisteredSubject[]
}
export interface StudentSemesterList {
  institution_id: string
  items: StudentSemester[]
}

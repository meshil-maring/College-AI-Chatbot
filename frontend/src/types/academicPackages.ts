export type AcademicValue = string | number | boolean | null | AcademicValue[] | { [key: string]: AcademicValue }
export type PackageRecord = Record<string, AcademicValue>
export type PackageCollection =
  | 'curricula'
  | 'curriculum_subjects'
  | 'packages'
  | 'package_subjects'
  | 'classes'
  | 'class_packages'
  | 'class_subjects'
  | 'class_responsibilities'
  | 'placements'
  | 'assignments'
  | 'requests'
  | 'history'
export type PackageOption =
  | 'programs'
  | 'batches'
  | 'academic_years'
  | 'semesters'
  | 'subjects'
  | 'sections'
  | 'registrations'
  | 'responsibilities'
export type PackageCapability =
  | 'manage'
  | 'manage_curriculum'
  | 'manage_class'
  | 'prepare_teaching'
  | 'assign'
  | 'change'
  | 'review'
  | 'select'
  | 'request'

export interface AcademicPackageCatalogue {
  institution_id: string
  capabilities: PackageCapability[]
  records: Partial<Record<PackageCollection, PackageRecord[]>>
  options: Partial<Record<PackageOption, PackageRecord[]>>
}

export interface AcademicPackageCommands {
  save_curriculum: { curriculum_id?: string; program_id: string; name: string; code: string; version: number }
  set_curriculum_subject: {
    curriculum_id: string
    course_id: string
    study_semester: number
    course_type: string
    is_core: boolean
  }
  save_package: {
    package_id?: string
    curriculum_id: string
    study_semester: number
    name: string
    code: string
    curriculum_subject_ids: string[]
  }
  save_class: {
    class_id?: string
    program_id: string
    batch_id: string
    semester_id: string
    study_semester: number
    section_code: string
    curriculum_id: string
    student_choice_enabled: boolean
    change_cutoff?: string | null
  }
  set_class_package: { class_id: string; package_id: string; enabled: boolean }
  set_class_subject: { class_id: string; curriculum_subject_id: string; section_id: string }
  prepare_class_teaching: { class_id: string }
  set_class_responsibility: { class_id: string; responsibility_id: string; enabled: boolean }
  place_student: { class_id: string; registration_id: string }
  assign_package: { placement_id: string; package_id: string }
  change_package: { assignment_id: string; package_id: string; expected_revision: number; reason: string }
  request_change: { assignment_id: string; package_id: string; reason: string }
  review_request: { request_id: string; approve: boolean; reason: string }
}

export type PackageOperation = keyof AcademicPackageCommands

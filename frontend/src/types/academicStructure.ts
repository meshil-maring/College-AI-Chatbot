import type { AcademicContext, CourseType } from './academicSetup.ts'

export interface StructureRecord extends AcademicContext {
  created_at: string
  updated_at: string
}
export interface ProgramSemester extends StructureRecord {
  program_semester_id: string
  program_id: string
  name: string
  code: string
  semester_number: number
}
export interface CurriculumVersion extends StructureRecord {
  curriculum_version_id: string
  program_id: string
  academic_year_id: string
  name: string
  version: string
  total_semesters: number
  description: string | null
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
}
export interface CurriculumSubject extends StructureRecord {
  curriculum_subject_id: string
  curriculum_version_id: string
  program_semester_id: string
  course_id: string
  course_type: CourseType
  is_required: boolean
}
export interface AdmissionCohort extends StructureRecord {
  admission_cohort_id: string
  program_id: string
  curriculum_version_id: string
  academic_year_id: string
  name: string
  code: string
  start_year: number
  end_year: number
  expected_count: number | null
  description: string | null
  status: 'active' | 'completed' | 'inactive'
}
export interface AcademicSection extends StructureRecord {
  academic_section_id: string
  admission_cohort_id: string
  program_semester_id: string
  semester_id: string
  name: string
  code: string
  capacity: number | null
  description: string | null
}
export interface AcademicOffering extends StructureRecord {
  academic_offering_id: string
  academic_section_id: string
  curriculum_subject_id: string
  capacity: number | null
}
export interface StructureRecordMap {
  program_semesters: ProgramSemester
  curriculum_versions: CurriculumVersion
  curriculum_subjects: CurriculumSubject
  admission_cohorts: AdmissionCohort
  academic_sections: AcademicSection
  academic_offerings: AcademicOffering
}
export type StructureEntity = keyof StructureRecordMap
type StoredFields = keyof StructureRecord
export interface StructureCreateMap {
  program_semesters: Omit<ProgramSemester, StoredFields | 'program_semester_id'> & { is_active: boolean }
  curriculum_versions: Omit<CurriculumVersion, StoredFields | 'curriculum_version_id' | 'status' | 'published_at'> & {
    is_active: boolean
  }
  curriculum_subjects: Omit<CurriculumSubject, StoredFields | 'curriculum_subject_id'> & { is_active: boolean }
  admission_cohorts: Omit<AdmissionCohort, StoredFields | 'admission_cohort_id'>
  academic_sections: Omit<AcademicSection, StoredFields | 'academic_section_id'> & { is_active: boolean }
  academic_offerings: Omit<AcademicOffering, StoredFields | 'academic_offering_id'> & { is_active: boolean }
}
export interface StructureUpdateMap {
  program_semesters: Partial<Pick<ProgramSemester, 'name' | 'code' | 'is_active'>>
  curriculum_versions: Partial<Pick<CurriculumVersion, 'name' | 'description' | 'status' | 'is_active'>>
  curriculum_subjects: Partial<Pick<CurriculumSubject, 'course_type' | 'is_required' | 'is_active'>>
  admission_cohorts: Partial<Pick<AdmissionCohort, 'name' | 'code' | 'expected_count' | 'description' | 'status'>>
  academic_sections: Partial<Pick<AcademicSection, 'name' | 'capacity' | 'description' | 'is_active'>>
  academic_offerings: Partial<Pick<AcademicOffering, 'capacity' | 'is_active'>>
}
export interface AcademicActivity {
  id: string
  entity: string
  record_id: string
  action: string
  performed_at: string
  name: string | null
}
export interface StructureCatalogue {
  institution_id: string
  records: { [E in StructureEntity]?: StructureRecordMap[E][] }
  manageable: StructureEntity[]
  activities: AcademicActivity[]
}

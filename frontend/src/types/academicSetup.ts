export type AcademicEntity =
  | 'departments'
  | 'programs'
  | 'academic_years'
  | 'semesters'
  | 'courses'
  | 'program_courses'
  | 'course_offerings'
  | 'sections'
  | 'batches'
export type AcademicRecord = Record<string, string | number | boolean | null>
export interface OfferingEligibility {
  program_id: string
  course_id: string
  semester_id: string
  source: 'named_curriculum'
}
export interface AcademicCatalogue {
  institution_id: string
  records: Partial<Record<AcademicEntity, AcademicRecord[]>>
  manageable: AcademicEntity[]
  offering_eligibility?: OfferingEligibility[]
}

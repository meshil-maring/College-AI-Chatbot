export type AcademicEntity = 'departments' | 'programs' | 'academic_years' | 'semesters' | 'courses' | 'program_courses' | 'course_offerings' | 'sections'
export type AcademicRecord = Record<string, string | number | boolean | null>
export interface AcademicCatalogue {
  institution_id: string
  records: Partial<Record<AcademicEntity, AcademicRecord[]>>
  manageable: AcademicEntity[]
}

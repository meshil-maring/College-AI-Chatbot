/** Descendant institution_id is API context derived from tenant-scoped joins. */
export type AcademicEntity =
  | 'departments'
  | 'programs'
  | 'academic_years'
  | 'semesters'
  | 'courses'
  | 'program_courses'
  | 'course_offerings'
  | 'sections'

export interface AcademicContext {
  institution_id: string
  is_active: boolean
}
export interface AcademicBaseRecord extends AcademicContext {
  name: string
  code: string
}
export interface Department extends AcademicBaseRecord {
  department_id: string
  description: string | null
}
export interface DegreeProgram extends AcademicBaseRecord {
  program_id: string
  department_id: string
  description: string | null
  degree_type: string
  duration_years: number
  total_credits: number | null
}
export interface AcademicYear extends AcademicBaseRecord {
  academic_year_id: string
  start_date: string
  end_date: string
  is_current: boolean
}
export interface Semester extends AcademicBaseRecord {
  semester_id: string
  academic_year_id: string
  semester_number: number
  start_date: string
  end_date: string
  is_current: boolean
}
export interface Course extends AcademicBaseRecord {
  course_id: string
  department_id: string
  description: string | null
  credits: number | null
  lecture_hours: number | null
  tutorial_hours: number | null
  practical_hours: number | null
}
export type CourseType = 'core' | 'elective' | 'open_elective' | 'skill' | 'project'
export interface ProgramCourse extends AcademicContext {
  program_course_id: string
  program_id: string
  course_id: string
  semester_id: string | null
  course_type: CourseType
  is_required: boolean
}
export interface CourseOffering extends AcademicContext {
  course_offering_id: string
  course_id: string
  program_id: string
  academic_year_id: string
  semester_id: string
  capacity: number | null
}
export interface OfferingSection extends AcademicBaseRecord {
  section_id: string
  course_offering_id: string
  capacity: number | null
}
export interface AcademicRecordMap {
  departments: Department
  programs: DegreeProgram
  academic_years: AcademicYear
  semesters: Semester
  courses: Course
  program_courses: ProgramCourse
  course_offerings: CourseOffering
  sections: OfferingSection
}
export interface AcademicCreateMap {
  departments: Omit<Department, 'department_id' | 'institution_id'>
  programs: Omit<DegreeProgram, 'program_id' | 'institution_id'>
  academic_years: Omit<AcademicYear, 'academic_year_id' | 'institution_id'>
  semesters: Omit<Semester, 'semester_id' | 'institution_id'>
  courses: Omit<Course, 'course_id' | 'institution_id'>
  program_courses: Omit<ProgramCourse, 'program_course_id' | 'institution_id'>
  course_offerings: Omit<CourseOffering, 'course_offering_id' | 'institution_id'>
  sections: Omit<OfferingSection, 'section_id' | 'institution_id'>
}
export interface AcademicUpdateMap {
  departments: Partial<AcademicCreateMap['departments']>
  programs: Partial<Omit<AcademicCreateMap['programs'], 'department_id'>>
  academic_years: Partial<AcademicCreateMap['academic_years']>
  semesters: Partial<Omit<AcademicCreateMap['semesters'], 'academic_year_id'>>
  courses: Partial<Omit<AcademicCreateMap['courses'], 'department_id'>>
  program_courses: Partial<Omit<AcademicCreateMap['program_courses'], 'program_id' | 'course_id' | 'semester_id'>>
  course_offerings: Partial<Pick<AcademicCreateMap['course_offerings'], 'capacity' | 'is_active'>>
  sections: Partial<Omit<AcademicCreateMap['sections'], 'course_offering_id' | 'code'>>
}
export type AcademicRecord = AcademicRecordMap[AcademicEntity]
export type AcademicCreate = AcademicCreateMap[AcademicEntity]
export interface AcademicCatalogue {
  institution_id: string
  records: { [E in AcademicEntity]?: AcademicRecordMap[E][] }
  manageable: AcademicEntity[]
}

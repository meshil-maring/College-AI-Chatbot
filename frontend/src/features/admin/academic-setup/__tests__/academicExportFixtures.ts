import { catalogue, department, program, year } from './AcademicSetup.support.ts'
import type {
  Course,
  Semester,
  ProgramCourse,
  CourseOffering,
  OfferingSection,
} from '../../../../types/academicSetup.ts'

export const semester: Semester = {
  institution_id: 'institution-1',
  semester_id: 'semester-1',
  academic_year_id: year.academic_year_id,
  name: 'Autumn',
  code: 'AUT',
  semester_number: 1,
  start_date: '2026-07-01',
  end_date: '2026-12-31',
  is_current: false,
  is_active: true,
}
export const course: Course = {
  institution_id: 'institution-1',
  course_id: 'course-1',
  department_id: department.department_id,
  name: 'Data Mining',
  code: 'DM',
  description: null,
  credits: 3.5,
  lecture_hours: 3,
  tutorial_hours: null,
  practical_hours: 2,
  is_active: true,
}
export const link: ProgramCourse = {
  institution_id: 'institution-1',
  program_course_id: 'link-1',
  program_id: program.program_id,
  course_id: course.course_id,
  semester_id: null,
  course_type: 'core',
  is_required: true,
  is_active: true,
}
export const offering: CourseOffering = {
  institution_id: 'institution-1',
  course_offering_id: 'offering-1',
  program_id: program.program_id,
  course_id: course.course_id,
  academic_year_id: year.academic_year_id,
  semester_id: semester.semester_id,
  capacity: 60,
  is_active: true,
}
export const section: OfferingSection = {
  institution_id: 'institution-1',
  section_id: 'section-1',
  course_offering_id: offering.course_offering_id,
  name: 'Section A',
  code: 'A',
  capacity: 30,
  is_active: true,
}
export function populateExportCatalogue() {
  catalogue.records = {
    departments: [structuredClone(department)],
    programs: [structuredClone(program)],
    academic_years: [structuredClone(year)],
    semesters: [structuredClone(semester)],
    courses: [structuredClone(course)],
    program_courses: [structuredClone(link)],
    course_offerings: [structuredClone(offering)],
    sections: [structuredClone(section)],
  }
  catalogue.manageable = [
    'departments',
    'programs',
    'academic_years',
    'semesters',
    'courses',
    'program_courses',
    'course_offerings',
    'sections',
  ]
}

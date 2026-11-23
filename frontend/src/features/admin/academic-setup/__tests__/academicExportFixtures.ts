import { catalogue, department, program, year } from './AcademicSetup.support.ts'
import type { Course, Semester } from '../../../../types/academicSetup.ts'

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
export function populateExportCatalogue() {
  catalogue.records = {
    departments: [structuredClone(department)],
    programs: [structuredClone(program)],
    academic_years: [structuredClone(year)],
    semesters: [structuredClone(semester)],
    courses: [structuredClone(course)],
  }
  catalogue.manageable = ['departments', 'programs', 'academic_years', 'semesters', 'courses']
}

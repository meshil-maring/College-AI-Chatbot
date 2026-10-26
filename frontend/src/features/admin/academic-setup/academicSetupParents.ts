import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'

/** Keep browser choices inside the server-selected tenant and active ancestry. */
export function academicParents(source: AcademicCatalogue, entity: AcademicEntity) {
  const records = Object.fromEntries(
    Object.entries(source.records).map(([key, rows]) => [
      key,
      (rows as AcademicRecord[]).filter((row) => row.institution_id === source.institution_id),
    ]),
  ) as AcademicCatalogue['records']
  const catalogue = { ...source, records }
  const departments = new Set(records.departments?.filter((row) => row.is_active).map((row) => row.department_id))
  const programs = new Set(
    records.programs?.filter((row) => row.is_active && departments.has(row.department_id)).map((row) => row.program_id),
  )
  const courses = new Set(
    records.courses?.filter((row) => row.is_active && departments.has(row.department_id)).map((row) => row.course_id),
  )
  const years = new Set(records.academic_years?.filter((row) => row.is_active).map((row) => row.academic_year_id))
  const semesters = new Set(
    records.semesters?.filter((row) => row.is_active && years.has(row.academic_year_id)).map((row) => row.semester_id),
  )
  const links = (records.program_courses ?? []).filter(
    (row) =>
      row.is_active &&
      programs.has(row.program_id) &&
      courses.has(row.course_id) &&
      (!row.semester_id || semesters.has(row.semester_id)),
  )
  const offerings = (records.course_offerings ?? []).filter(
    (row) =>
      row.is_active &&
      years.has(row.academic_year_id) &&
      semesters.has(row.semester_id) &&
      records.semesters?.some(
        (semester) => semester.semester_id === row.semester_id && semester.academic_year_id === row.academic_year_id,
      ) &&
      links.some(
        (link) =>
          link.program_id === row.program_id &&
          link.course_id === row.course_id &&
          (!link.semester_id || link.semester_id === row.semester_id),
      ),
  )
  let issue: string | null = null
  if (['programs', 'courses'].includes(entity) && !departments.size)
    issue = 'An active department must be available before adding a record.'
  if (entity === 'semesters' && !years.size)
    issue = 'An active academic year must be available before adding a semester.'
  if (entity === 'program_courses' && (!programs.size || !courses.size))
    issue = 'An active program and course must be available before linking them.'
  if (entity === 'course_offerings' && (!links.length || !semesters.size))
    issue = 'An active program-course link and semester must be available before adding an offering.'
  if (entity === 'sections' && !offerings.length)
    issue = 'An active course offering must be available before adding a section.'
  return { catalogue, departments, programs, courses, years, semesters, links, offerings, issue }
}

import type { AcademicCatalogue, AcademicRecord } from '../../../types/academicSetup.ts'

function named(id: string, rows: { name: string; code: string }[] | undefined, key: string): string {
  const row = rows?.find((item) => (item as unknown as Record<string, unknown>)[key] === id)
  return row ? `${row.name} (${row.code})` : `Unavailable (${id})`
}
export function academicRecordLabel(record: AcademicRecord, catalogue: AcademicCatalogue): string {
  const rows = catalogue.records
  if ('name' in record) return `${record.name} (${record.code})`
  const parts = [
    named(record.program_id, rows.programs, 'program_id'),
    named(record.course_id, rows.courses, 'course_id'),
  ]
  if (record.semester_id) parts.push(named(record.semester_id, rows.semesters, 'semester_id'))
  if ('academic_year_id' in record) parts.push(named(record.academic_year_id, rows.academic_years, 'academic_year_id'))
  return parts.join(' / ')
}
export function academicRecordContext(record: AcademicRecord, catalogue: AcademicCatalogue): string {
  const rows = catalogue.records
  if ('section_id' in record) {
    const offering = rows.course_offerings?.find((row) => row.course_offering_id === record.course_offering_id)
    return offering ? academicRecordLabel(offering, catalogue) : `Offering unavailable (${record.course_offering_id})`
  }
  if ('department_id' in record && ('program_id' in record || 'course_id' in record))
    return named(record.department_id, rows.departments, 'department_id')
  if ('semester_number' in record)
    return `${named(record.academic_year_id, rows.academic_years, 'academic_year_id')} / Semester ${record.semester_number}`
  if ('course_type' in record)
    return `${record.course_type.replaceAll('_', ' ')} / ${record.is_required ? 'Required' : 'Optional'}`
  return ''
}

import type { AcademicCatalogue, AcademicRecord } from '../../../types/academicSetup.ts'

function named(id: string, rows: { name: string; code: string }[] | undefined, key: string): string {
  const row = rows?.find((item) => (item as unknown as Record<string, unknown>)[key] === id)
  return row ? `${row.name} (${row.code})` : `Unavailable (${id})`
}
export function academicRecordContext(record: AcademicRecord, catalogue: AcademicCatalogue): string {
  const rows = catalogue.records
  if ('department_id' in record && ('degree_type' in record || 'credits' in record))
    return named(record.department_id, rows.departments, 'department_id')
  if ('semester_number' in record)
    return `${named(record.academic_year_id, rows.academic_years, 'academic_year_id')} / Semester ${record.semester_number}`
  return ''
}

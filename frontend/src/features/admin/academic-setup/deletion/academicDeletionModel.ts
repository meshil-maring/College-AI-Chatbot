import type {
  AcademicCatalogue,
  AcademicYear,
  Department,
  DegreeProgram,
  Semester,
} from '../../../../types/academicSetup.ts'
import type { AcademicSection, StructureCatalogue } from '../../../../types/academicStructure.ts'

export const deletionConfig = {
  departments: { label: 'Department', key: 'department_id', focusTarget: '.departments-page h1' },
  programs: { label: 'Program', key: 'program_id', focusTarget: '.programs-page h1' },
  academic_years: { label: 'Academic Year', key: 'academic_year_id', focusTarget: '.calendar-page h1' },
  semesters: { label: 'Semester', key: 'semester_id', focusTarget: '.calendar-page h1' },
  academic_sections: { label: 'Section', key: 'academic_section_id', focusTarget: '.sections-page h1' },
} as const
export type DeletionEntity = keyof typeof deletionConfig
export type DeletionRecord = Department | DegreeProgram | AcademicYear | Semester | AcademicSection

export function deletionId(entity: DeletionEntity, record: DeletionRecord) {
  const value: unknown = Reflect.get(record, deletionConfig[entity].key)
  return typeof value === 'string' ? value : undefined
}

export function deletionRecords(
  entity: DeletionEntity,
  catalogue?: AcademicCatalogue,
  structure?: StructureCatalogue,
): DeletionRecord[] | undefined {
  return entity === 'academic_sections' ? structure?.records.academic_sections : catalogue?.records[entity]
}

export function deletionBlocker(
  entity: DeletionEntity,
  record: DeletionRecord | null,
  catalogue?: AcademicCatalogue,
  structure?: StructureCatalogue,
) {
  if (!record) return null
  if ('is_current' in record && record.is_current)
    return 'Select a replacement current academic year or semester before deleting this record.'
  const id = deletionId(entity, record)
  let links: (string | false | undefined)[]
  switch (entity) {
    case 'departments':
      links = [
        catalogue?.records.programs?.some((item) => item.department_id === id) && 'programs',
        catalogue?.records.courses?.some((item) => item.department_id === id) && 'subjects',
      ]
      break
    case 'programs':
      links = [
        catalogue?.records.program_courses?.some((item) => item.program_id === id) && 'subject mappings',
        catalogue?.records.course_offerings?.some((item) => item.program_id === id) && 'course offerings',
      ]
      break
    case 'academic_years':
      links = [
        catalogue?.records.semesters?.some((item) => item.academic_year_id === id) && 'semesters',
        catalogue?.records.course_offerings?.some((item) => item.academic_year_id === id) && 'course offerings',
        structure?.records.curriculum_versions?.some((item) => item.academic_year_id === id) && 'curricula',
        structure?.records.admission_cohorts?.some((item) => item.academic_year_id === id) && 'batches',
      ]
      break
    case 'semesters':
      links = [
        catalogue?.records.program_courses?.some((item) => item.semester_id === id) && 'subject mappings',
        catalogue?.records.course_offerings?.some((item) => item.semester_id === id) && 'course offerings',
        structure?.records.academic_sections?.some((item) => item.semester_id === id) && 'class sections',
      ]
      break
    case 'academic_sections':
      links = [
        structure?.records.academic_offerings?.some((item) => item.academic_section_id === id) && 'subject offerings',
      ]
      break
  }
  const names = links.filter(Boolean)
  return names.length
    ? `This ${deletionConfig[entity].label.toLowerCase()} has linked ${names.join(' and ')}, including inactive records. It cannot be deleted.`
    : null
}

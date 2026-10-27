import type { StructureEntity } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'
import type { StructureRow } from './structureForm.ts'

export function structureLabel(entity: StructureEntity, row: StructureRow, state: AcademicStructureState) {
  if ('name' in row) return row.name
  const records = state.structure?.records
  if (entity === 'curriculum_subjects' && 'course_id' in row)
    return (
      state.catalogue?.records.courses?.find(
        (item) => item.institution_id === state.context.institutionId && item.course_id === row.course_id,
      )?.name ?? 'Subject unavailable'
    )
  if ('academic_section_id' in row && 'curriculum_subject_id' in row) {
    const section = records?.academic_sections?.find((item) => item.academic_section_id === row.academic_section_id)
    const mapping = records?.curriculum_subjects?.find(
      (item) => item.curriculum_subject_id === row.curriculum_subject_id,
    )
    const course = state.catalogue?.records.courses?.find(
      (item) => item.institution_id === state.context.institutionId && item.course_id === mapping?.course_id,
    )
    return `${course?.name ?? 'Subject unavailable'} · ${section?.name ?? 'Section unavailable'}`
  }
  return 'Academic record'
}
export function structureContextLabel(row: StructureRow, state: AcademicStructureState) {
  if ('program_id' in row)
    return (
      state.catalogue?.records.programs?.find(
        (item) => item.institution_id === state.context.institutionId && item.program_id === row.program_id,
      )?.name ?? 'Program unavailable'
    )
  if ('program_semester_id' in row)
    return (
      state.structure?.records.program_semesters?.find((item) => item.program_semester_id === row.program_semester_id)
        ?.name ?? 'Semester unavailable'
    )
  if ('academic_section_id' in row)
    return (
      state.structure?.records.academic_sections?.find((item) => item.academic_section_id === row.academic_section_id)
        ?.code ?? 'Section unavailable'
    )
  return '—'
}

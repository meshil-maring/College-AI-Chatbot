import type { AcademicSection, StructureCatalogue, StructureEntity } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'
import type { StructureRow } from './structureForm.ts'

/** Section codes repeat across batches and semesters, so lists name the batch and semester too. */
export function academicSectionLabel(section: AcademicSection, records?: StructureCatalogue['records']) {
  const batch = records?.admission_cohorts?.find((item) => item.admission_cohort_id === section.admission_cohort_id)
  const stage = records?.program_semesters?.find((item) => item.program_semester_id === section.program_semester_id)
  return [section.name, batch?.code, stage?.name].filter(Boolean).join(' · ')
}

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
    return `${course?.name ?? 'Subject unavailable'} · ${section ? academicSectionLabel(section, records) : 'Section unavailable'}`
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

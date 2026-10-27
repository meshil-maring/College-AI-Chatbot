import type { StructureEntity } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'
import type { StructureDraft } from './structureFields.ts'
import { structureFields } from './structureFields.ts'
import type { StructureRow } from './structureForm.ts'

export function structureCreationIssue(
  entity: StructureEntity,
  state: AcademicStructureState,
  defaults: StructureDraft,
) {
  const fields = structureFields(entity, state, defaults)
  if (entity === 'program_semesters' && !fields.find((field) => field.key === 'program_id')?.options?.length)
    return 'Create an active program before adding its progression semesters.'
  if (
    entity === 'curriculum_versions' &&
    fields.some((field) => ['program_id', 'academic_year_id'].includes(field.key) && !field.options?.length)
  )
    return 'Create an active program and academic year before creating a curriculum.'
  if (entity === 'curriculum_subjects') {
    const version = state.structure?.records.curriculum_versions?.find(
      (item) => item.curriculum_version_id === defaults.curriculum_version_id,
    )
    if (version && version.status !== 'draft')
      return 'Published curriculum mappings are preserved. Select or create a draft version to make changes.'
    if (
      !fields.find((field) => field.key === 'curriculum_version_id')?.options?.length ||
      !fields.find((field) => field.key === 'course_id')?.options?.length ||
      !state.structure?.records.program_semesters?.some((item) => item.is_active)
    )
      return 'Create a draft curriculum, program semester and active subject before adding mappings.'
  }
  if (
    entity === 'academic_offerings' &&
    (!fields.find((field) => field.key === 'academic_section_id')?.options?.length ||
      !state.structure?.records.curriculum_subjects?.some((item) => item.is_active))
  )
    return 'Create an active section and matching curriculum subject before adding offerings.'
  return undefined
}
export function structureCanEdit(entity: StructureEntity, row: StructureRow, state: AcademicStructureState) {
  if (!state.canManage(entity)) return false
  if (entity === 'curriculum_subjects' && 'curriculum_version_id' in row)
    return (
      state.structure?.records.curriculum_versions?.some(
        (version) => version.curriculum_version_id === row.curriculum_version_id && version.status === 'draft',
      ) ?? false
    )
  return true
}

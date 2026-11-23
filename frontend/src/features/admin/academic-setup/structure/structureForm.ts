import type { StructureEntity, StructureRecordMap } from '../../../../types/academicStructure.ts'
import type { StructureDraft, StructureField } from './structureFields.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'

export type StructureRow = StructureRecordMap[StructureEntity]
export function structureId(entity: StructureEntity, row: StructureRow): string {
  return String((row as unknown as Record<string, unknown>)[`${entity.slice(0, -1)}_id`])
}
export function structureDraft(row?: StructureRow, defaults: StructureDraft = {}): StructureDraft {
  return row
    ? Object.fromEntries(
        Object.entries(row).map(([key, value]) => [
          key,
          typeof value === 'boolean' ? value : value == null ? '' : String(value),
        ]),
      )
    : {
        name: '',
        code: '',
        program_id: '',
        academic_year_id: '',
        semester_number: '1',
        version: '1.0',
        total_semesters: '8',
        description: '',
        is_active: true,
        status: 'draft',
        curriculum_version_id: '',
        program_semester_id: '',
        course_id: '',
        course_type: 'core',
        is_required: true,
        academic_section_id: '',
        curriculum_subject_id: '',
        capacity: '',
        ...defaults,
      }
}
/** Two semesters per program year, as the starting length of a new curriculum. */
export function defaultSemesterCount(state: AcademicStructureState, programId: string, fallback: string | boolean) {
  const duration = state.catalogue?.records.programs?.find((item) => item.program_id === programId)?.duration_years
  if (!duration || duration <= 0) return { total_semesters: fallback }
  return { total_semesters: String(Math.min(32, Math.max(1, Math.ceil(duration * 2)))) }
}
export function structurePayload(fields: StructureField[], draft: StructureDraft, row?: StructureRow) {
  const original = row ? structureDraft(row) : undefined
  return Object.fromEntries(
    fields
      .filter(
        (field) =>
          !(row && (field.immutable || field.frozen)) &&
          (row ? original?.[field.key] !== draft[field.key] : field.key !== 'status'),
      )
      .map((field) => [
        field.key,
        field.type === 'checkbox'
          ? Boolean(draft[field.key])
          : field.type === 'number'
            ? draft[field.key] === ''
              ? null
              : Number(draft[field.key])
            : typeof draft[field.key] === 'string'
              ? String(draft[field.key]).trim() || null
              : draft[field.key],
      ]),
  )
}
export function validateStructureFields(fields: StructureField[], draft: StructureDraft, row?: StructureRow) {
  for (const field of fields) {
    if ((row && (field.immutable || field.frozen)) || field.type === 'checkbox') continue
    const value = String(draft[field.key] ?? '').trim()
    if (field.required && !value) return `Enter or select ${field.label.toLowerCase()}.`
    if (field.type === 'select' && value && !field.options?.some((option) => option.value === value))
      return `Select an available ${field.label.toLowerCase()}.`
    if (field.type === 'number' && /^\d+$/.test(value) && field.max !== undefined && Number(value) > field.max)
      return `${field.label} cannot be more than ${field.max}.`
    if (
      field.type === 'number' &&
      value &&
      (!/^\d+$/.test(value) ||
        !Number.isSafeInteger(Number(value)) ||
        Number(value) < (field.min ?? 0) ||
        Number(value) > (field.max ?? 2147483647))
    )
      return `Enter a valid whole number for ${field.label.toLowerCase()}.`
  }
  return undefined
}

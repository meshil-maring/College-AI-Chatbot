import type { StructureEntity } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'

export interface StructureField {
  key: string
  label: string
  type?: 'text' | 'number' | 'select' | 'textarea' | 'checkbox'
  required?: boolean
  immutable?: boolean
  frozen?: boolean
  min?: number
  max?: number
  options?: { value: string; label: string }[]
  help?: string
}
export type StructureDraft = Record<string, string | boolean>
export const structureTitles: Record<StructureEntity, string> = {
  program_semesters: 'Program Semesters',
  curriculum_versions: 'Curriculum Versions',
  curriculum_subjects: 'Curriculum Subjects',
  admission_cohorts: 'Batches',
  academic_sections: 'Sections',
  academic_offerings: 'Academic Offerings',
}
export const structureSingular: Record<StructureEntity, string> = {
  program_semesters: 'Program Semester',
  curriculum_versions: 'Curriculum',
  curriculum_subjects: 'Subject Mapping',
  admission_cohorts: 'Batch',
  academic_sections: 'Section',
  academic_offerings: 'Academic Offering',
}
export function structureFields(
  entity: StructureEntity,
  state: AcademicStructureState,
  draft: StructureDraft,
): StructureField[] {
  const base = state.catalogue?.records
  const records = state.structure?.records
  const tenant = state.context.institutionId
  const programs =
    base?.programs?.filter(
      (item) =>
        item.institution_id === tenant &&
        item.is_active &&
        base.departments?.some(
          (parent) =>
            parent.institution_id === tenant && parent.department_id === item.department_id && parent.is_active,
        ),
    ) ?? []
  const years = base?.academic_years?.filter((item) => item.institution_id === tenant && item.is_active) ?? []
  const field = (key: string, label: string, extra: Partial<StructureField> = {}): StructureField => ({
    key,
    label,
    required: true,
    ...extra,
  })
  const program = field('program_id', 'Program', {
    type: 'select',
    immutable: true,
    options: programs.map((item) => ({ value: item.program_id, label: item.name })),
  })
  const year = field('academic_year_id', 'Academic Year', {
    type: 'select',
    immutable: true,
    options: years.map((item) => ({ value: item.academic_year_id, label: item.name })),
  })
  const active = field('is_active', 'Active', { type: 'checkbox', required: false })
  if (entity === 'program_semesters')
    return [
      program,
      field('name', 'Semester Name'),
      field('code', 'Semester Code'),
      field('semester_number', 'Semester Number', {
        type: 'number',
        min: 1,
        max: 32,
        immutable: true,
        help: 'Program progression, separate from dated teaching terms.',
      }),
      active,
    ]
  if (entity === 'curriculum_versions')
    return [
      program,
      year,
      field('name', 'Curriculum Name'),
      field('version', 'Version', { immutable: true }),
      field('total_semesters', 'Total Semesters', {
        type: 'number',
        min: 1,
        max: 32,
        immutable: true,
      }),
      field('description', 'Description', { type: 'textarea', required: false }),
      active,
      field('status', 'Publication Status', {
        type: 'select',
        options: [
          { value: 'draft', label: 'Draft' },
          { value: 'published', label: 'Published' },
          { value: 'archived', label: 'Archived' },
        ],
        help: 'Published versions and their subject mappings are preserved for assigned batches.',
      }),
    ]
  if (entity === 'curriculum_subjects') {
    const version = records?.curriculum_versions?.find(
      (item) => item.curriculum_version_id === draft.curriculum_version_id,
    )
    return [
      field('curriculum_version_id', 'Curriculum Version', {
        type: 'select',
        immutable: true,
        options: records?.curriculum_versions
          ?.filter((item) => item.is_active && item.status === 'draft')
          .map((item) => ({ value: item.curriculum_version_id, label: `${item.name} · v${item.version}` })),
      }),
      field('program_semester_id', 'Program Semester', {
        type: 'select',
        immutable: true,
        options: records?.program_semesters
          ?.filter(
            (item) =>
              item.is_active &&
              item.program_id === version?.program_id &&
              item.semester_number <= version.total_semesters,
          )
          .map((item) => ({ value: item.program_semester_id, label: item.name })),
      }),
      field('course_id', 'Subject', {
        type: 'select',
        immutable: true,
        options: base?.courses
          ?.filter(
            (item) =>
              item.institution_id === tenant &&
              item.is_active &&
              base.departments?.some(
                (parent) =>
                  parent.institution_id === tenant && parent.department_id === item.department_id && parent.is_active,
              ),
          )
          .map((item) => ({ value: item.course_id, label: `${item.name} (${item.code})` })),
      }),
      field('course_type', 'Subject Type', {
        type: 'select',
        options: ['core', 'elective', 'open_elective', 'skill', 'project'].map((value) => ({
          value,
          label: value.replace('_', ' '),
        })),
      }),
      field('is_required', 'Required Subject', { type: 'checkbox', required: false }),
      active,
    ]
  }
  if (entity === 'academic_offerings') {
    const section = records?.academic_sections?.find((item) => item.academic_section_id === draft.academic_section_id)
    const cohort = records?.admission_cohorts?.find((item) => item.admission_cohort_id === section?.admission_cohort_id)
    return [
      field('academic_section_id', 'Section', {
        type: 'select',
        immutable: true,
        options: records?.academic_sections
          ?.filter((item) => item.is_active)
          .map((item) => ({ value: item.academic_section_id, label: `${item.name} (${item.code})` })),
      }),
      field('curriculum_subject_id', 'Curriculum Subject', {
        type: 'select',
        immutable: true,
        options: records?.curriculum_subjects
          ?.filter(
            (item) =>
              item.is_active &&
              item.curriculum_version_id === cohort?.curriculum_version_id &&
              item.program_semester_id === section?.program_semester_id,
          )
          .map((item) => ({
            value: item.curriculum_subject_id,
            label:
              base?.courses?.find((course) => course.institution_id === tenant && course.course_id === item.course_id)
                ?.name ?? 'Subject unavailable',
          })),
      }),
      field('capacity', 'Maximum Capacity', { type: 'number', min: 0, max: 2147483647, required: false }),
      active,
    ]
  }
  return []
}

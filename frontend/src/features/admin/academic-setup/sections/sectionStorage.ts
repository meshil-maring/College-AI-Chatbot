import type { AcademicSection } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../structure/useAcademicStructure.ts'
import type { SectionRecord } from './sectionModel.ts'
import { batchChoices } from '../batches/batchStorage.ts'

export function storedSection(record: AcademicSection): SectionRecord {
  return {
    id: record.academic_section_id,
    name: record.name,
    code: record.code,
    batchId: record.admission_cohort_id,
    programSemesterId: record.program_semester_id,
    semesterId: record.semester_id,
    capacity: record.capacity == null ? '' : String(record.capacity),
    description: record.description ?? '',
    status: record.is_active ? 'active' : 'inactive',
    studentCount: null,
    color: ['gold', 'purple', 'teal', 'orange', 'blue', 'green', 'pink'][
      [...record.code].reduce((sum, character) => sum + character.charCodeAt(0), 0) % 7
    ],
  }
}
export function sectionChoices(source: AcademicStructureState) {
  const choices = batchChoices(source)
  const batches = (source.structure?.records.admission_cohorts ?? []).map((record) => ({
    id: record.admission_cohort_id,
    name: record.name,
    programId: record.program_id,
    academicYear:
      choices.years.find((year) => year.academic_year_id === record.academic_year_id)?.name ?? 'Unavailable',
    active: record.is_active && choices.programs.some((program) => program.id === record.program_id && program.active),
    totalSemesters: source.structure?.records.curriculum_versions?.find(
      (version) => version.curriculum_version_id === record.curriculum_version_id,
    )?.total_semesters,
  }))
  const terms = (source.catalogue?.records.semesters ?? [])
    .filter((record) => record.institution_id === source.context.institutionId)
    .map((term) => ({
      ...term,
      available:
        term.is_active &&
        choices.years.some((year) => year.academic_year_id === term.academic_year_id && year.is_active),
    }))
  return {
    ...choices,
    batches,
    terms,
    stages: source.structure?.records.program_semesters ?? [],
    yearLabels: [...new Set(batches.map((batch) => batch.academicYear))],
  }
}

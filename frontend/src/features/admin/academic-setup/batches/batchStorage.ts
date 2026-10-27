import type { AdmissionCohort } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../structure/useAcademicStructure.ts'
import type { BatchRecord } from './batchModel.ts'

export function storedBatch(record: AdmissionCohort): BatchRecord {
  return {
    id: record.admission_cohort_id,
    name: record.name,
    code: record.code,
    programId: record.program_id,
    curriculumId: record.curriculum_version_id,
    academicYear: record.academic_year_id,
    startYear: String(record.start_year),
    endYear: String(record.end_year),
    expectedCount: record.expected_count == null ? '' : String(record.expected_count),
    description: record.description ?? '',
    status: record.status,
    studentCount: null,
  }
}
export function batchChoices(source: AcademicStructureState) {
  const catalogue = source.catalogue
  const tenant = source.context.institutionId
  const programs = (catalogue?.records.programs ?? [])
    .filter((item) => item.institution_id === tenant)
    .map((item) => ({
      id: item.program_id,
      name: item.name,
      code: item.code,
      duration: item.duration_years,
      color: 'gold',
      active:
        item.is_active &&
        Boolean(
          catalogue?.records.departments?.some(
            (parent) =>
              parent.institution_id === tenant && parent.department_id === item.department_id && parent.is_active,
          ),
        ),
    }))
  const curricula = (source.structure?.records.curriculum_versions ?? []).map((item) => ({
    id: item.curriculum_version_id,
    programId: item.program_id,
    version: item.version,
    active: item.is_active && item.status === 'published',
  }))
  const years = (catalogue?.records.academic_years ?? []).filter((item) => item.institution_id === tenant)
  return { programs, curricula, years }
}

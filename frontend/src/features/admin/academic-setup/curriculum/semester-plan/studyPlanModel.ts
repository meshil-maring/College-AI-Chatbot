import type { CurriculumVersion } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import type { AcademicCatalogue } from '../../../../../types/academicSetup.ts'

export function scopeStudyPlanState(state: AcademicStructureState): AcademicStructureState {
  return {
    ...state,
    catalogue: state.catalogue && {
      ...state.catalogue,
      records: Object.fromEntries(
        Object.entries(state.catalogue.records).map(([entity, records]) => [
          entity,
          records.filter((record) => record.institution_id === state.context.institutionId),
        ]),
      ) as AcademicCatalogue['records'],
    },
  }
}

export function studyPlanSemesters(state: AcademicStructureState, version: CurriculumVersion) {
  return Array.from({ length: version.total_semesters }, (_, index) => {
    const number = index + 1
    const semester = state.structure?.records.program_semesters?.find(
      (item) => item.program_id === version.program_id && item.semester_number === number,
    )
    const subjects = (state.structure?.records.curriculum_subjects ?? []).filter(
      (item) =>
        item.curriculum_version_id === version.curriculum_version_id &&
        item.program_semester_id === semester?.program_semester_id,
    )
    return { number, semester, subjects }
  })
}

export function studyPlanCanChange(state: AcademicStructureState, version: CurriculumVersion) {
  const program = state.catalogue?.records.programs?.find((item) => item.program_id === version.program_id)
  return Boolean(
    version.status === 'draft' &&
    version.is_active &&
    program?.is_active &&
    state.catalogue?.records.departments?.some(
      (item) => item.department_id === program.department_id && item.is_active,
    ) &&
    state.catalogue?.records.academic_years?.some(
      (item) => item.academic_year_id === version.academic_year_id && item.is_active,
    ),
  )
}

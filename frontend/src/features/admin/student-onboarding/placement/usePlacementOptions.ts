import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { getAcademicStructure } from '../../../../services/admin/academicStructure.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'

const structureKey = (identity: string) => ['admin', identity, 'student-onboarding-structure'] as const

/** Active batches and sections a new student can be placed in, plus the description of one choice. */
export function usePlacementOptions(accessToken: string, identity: string, enabled: boolean, sectionId: string) {
  const structure = useApiQuery<StructureCatalogue>(
    structureKey(identity),
    () => getAcademicStructure(accessToken),
    enabled,
    { cache: 'navigation' },
  )
  const records = structure.data?.records
  const cohorts = records?.admission_cohorts ?? []
  const sections = (records?.academic_sections ?? []).filter((section) => {
    const cohort = cohorts.find((item) => item.admission_cohort_id === section.admission_cohort_id)
    return section.is_active && cohort?.status === 'active'
  })
  const selectedSection = sections.find((section) => section.academic_section_id === sectionId)
  const selectedCohort = cohorts.find((cohort) => cohort.admission_cohort_id === selectedSection?.admission_cohort_id)
  const selectedLabel =
    selectedSection && selectedCohort
      ? `${selectedCohort.code} · ${selectedCohort.name} · ${selectedSection.code} ${selectedSection.name}`
      : ''
  return {
    loading: structure.isPending,
    error: structure.error instanceof Error ? structure.error.message : '',
    cohorts,
    sections,
    selectedSection,
    selectedCohort,
    selectedLabel,
  }
}

export type PlacementOptions = ReturnType<typeof usePlacementOptions>

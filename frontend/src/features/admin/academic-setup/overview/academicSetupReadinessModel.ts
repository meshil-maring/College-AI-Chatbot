import type { AcademicCatalogue, DegreeProgram } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'
import type { AcademicPage } from './academicOverviewModel.ts'

export type ReadinessStatus = 'ready' | 'next' | 'waiting' | 'optional' | 'in-progress'
export interface ReadinessStep {
  title: string
  detail: string
  status: ReadinessStatus
}
interface ProgramReadiness {
  nextPage: AcademicPage
  nextAction: string
  nextExplanation: string
  steps: ReadinessStep[]
}

function activeRows<T extends { institution_id: string; is_active: boolean }>(
  rows: T[] | undefined,
  institutionId: string,
) {
  return rows?.filter((item) => item.institution_id === institutionId && item.is_active)
}

export function activeAcademicPrograms(catalogue?: AcademicCatalogue): DegreeProgram[] | undefined {
  const institutionId = catalogue?.institution_id
  const departments = activeRows(catalogue?.records.departments, institutionId ?? '')
  const departmentIds = new Set(departments?.map((item) => item.department_id))
  return activeRows(catalogue?.records.programs, institutionId ?? '')?.filter((program) =>
    departmentIds.has(program.department_id),
  )
}

function countLabel(count: number, label: string) {
  const plural = label.endsWith('curriculum') ? label.replace(/curriculum$/, 'curricula') : `${label}s`
  return `${count} ${count === 1 ? label : plural}`
}

export function programReadiness(
  catalogue: AcademicCatalogue,
  structure: StructureCatalogue | undefined,
  programId: string,
): ProgramReadiness | undefined {
  const academicYears = catalogue.records.academic_years
  const courses = catalogue.records.courses
  const versions = structure?.records.curriculum_versions
  const cohorts = structure?.records.admission_cohorts
  const academicSections = structure?.records.academic_sections
  const academicOfferings = structure?.records.academic_offerings
  if (
    !structure ||
    structure.institution_id !== catalogue.institution_id ||
    !catalogue.records.departments ||
    !catalogue.records.programs ||
    !academicYears ||
    !courses ||
    !versions ||
    !cohorts ||
    !academicSections ||
    !academicOfferings
  )
    return undefined
  const program = activeAcademicPrograms(catalogue)?.find((item) => item.program_id === programId)
  if (!program) return undefined
  const institutionId = catalogue.institution_id
  const subjects = courses.filter(
    (item) => item.institution_id === institutionId && item.department_id === program.department_id && item.is_active,
  ).length
  const years = activeRows(academicYears, institutionId)?.length ?? 0
  const programVersions = versions.filter(
    (item) => item.institution_id === institutionId && item.program_id === programId && item.is_active,
  )
  const drafts = programVersions.filter((item) => item.status === 'draft').length
  const published = programVersions.filter((item) => item.status === 'published').length
  const batches = cohorts.filter(
    (item) =>
      item.institution_id === institutionId &&
      item.program_id === programId &&
      item.is_active &&
      item.status === 'active',
  )
  const batchIds = new Set(batches.map((item) => item.admission_cohort_id))
  const sections = academicSections.filter(
    (item) => item.institution_id === institutionId && item.is_active && batchIds.has(item.admission_cohort_id),
  )
  const sectionIds = new Set(sections.map((item) => item.academic_section_id))
  const offerings = academicOfferings.filter(
    (item) => item.institution_id === institutionId && item.is_active && sectionIds.has(item.academic_section_id),
  ).length
  const foundationReady = Boolean(subjects && years)
  const curriculumReady = Boolean(published)
  const hasSections = sections.length > 0

  let nextPage: AcademicPage
  let nextAction: string
  let nextExplanation: string
  if (!subjects) {
    nextPage = 'subjects'
    nextAction = 'Add reusable subjects'
    nextExplanation = 'Programs share subjects with their department. Add at least one active subject.'
  } else if (!years) {
    nextPage = 'years'
    nextAction = 'Set up an academic year'
    nextExplanation = 'An active academic year is needed for this program’s curriculum and intake.'
  } else if (!published) {
    nextPage = drafts ? 'curriculum-subjects' : 'curriculum-versions'
    nextAction = drafts ? 'Continue this program’s draft curriculum' : 'Create this program’s curriculum'
    nextExplanation = 'Assign subjects to this program’s semesters, then publish the curriculum.'
  } else if (!batches.length) {
    nextPage = 'cohorts'
    nextAction = 'Create an intake batch for this program'
    nextExplanation = 'Assign the published curriculum to a group of incoming students.'
  } else if (!hasSections) {
    nextPage = 'sections'
    nextAction = 'Set up class sections (optional)'
    nextExplanation = 'Create sections only if this program needs separate enrollment or subject offerings.'
  } else if (!offerings) {
    nextPage = 'offerings'
    nextAction = 'Offer subjects to this program’s sections'
    nextExplanation = 'Choose which curriculum subjects each class group can take.'
  } else {
    nextPage = 'enrollments'
    nextAction = 'Enroll students in this program’s sections'
    nextExplanation = 'Assign approved students to the sections that offer their subjects.'
  }

  return {
    nextPage,
    nextAction,
    nextExplanation,
    steps: [
      {
        title: 'Foundations',
        detail: `${countLabel(subjects, 'active reusable subject')} · ${countLabel(years, 'active academic year')}`,
        status: foundationReady ? 'ready' : 'next',
      },
      {
        title: 'Curriculum',
        detail: `${countLabel(drafts, 'draft')} · ${countLabel(published, 'published curriculum')}`,
        status: !foundationReady ? 'waiting' : curriculumReady ? 'ready' : drafts ? 'in-progress' : 'next',
      },
      {
        title: 'Intake batch',
        detail: countLabel(batches.length, 'active batch'),
        status: !curriculumReady ? 'waiting' : batches.length ? 'ready' : 'next',
      },
      {
        title: 'Class delivery',
        detail: `${countLabel(sections.length, 'active section')} · ${countLabel(offerings, 'active subject offering')}`,
        status: !batches.length ? 'waiting' : hasSections ? (offerings ? 'ready' : 'in-progress') : 'optional',
      },
    ],
  }
}

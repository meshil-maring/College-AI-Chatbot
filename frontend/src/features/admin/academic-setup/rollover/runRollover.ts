import type { AcademicCreateMap, AcademicYear, Semester } from '../../../../types/academicSetup.ts'
import type {
  AcademicOffering,
  AcademicSection,
  ProgramSemester,
  StructureCreateMap,
} from '../../../../types/academicStructure.ts'
import type { RolloverPlan } from './rolloverPlan.ts'

export interface RolloverApi {
  createYear: (payload: AcademicCreateMap['academic_years']) => Promise<AcademicYear>
  createTerm: (payload: AcademicCreateMap['semesters']) => Promise<Semester>
  createStage: (payload: StructureCreateMap['program_semesters']) => Promise<ProgramSemester>
  createSection: (payload: StructureCreateMap['academic_sections']) => Promise<AcademicSection>
  createOffering: (payload: StructureCreateMap['academic_offerings']) => Promise<AcademicOffering>
}
export interface RolloverProgress {
  done: number
  total: number
  current: string
}

export function rolloverStepCount(plan: RolloverPlan) {
  const stages = new Set(plan.sections.filter((s) => !s.stageId).map((s) => `${s.programId}:${s.stageNumber}`))
  return (
    (plan.year.existing ? 0 : 1) +
    plan.terms.filter((term) => !term.existing).length +
    stages.size +
    plan.sections.filter((section) => !section.existingSectionId).length +
    plan.sections.reduce((count, section) => count + section.subjects.length, 0)
  )
}

/**
 * Creates the planned records in dependency order. It stops at the first
 * failure; because a fresh plan reuses everything already created, retrying is
 * simply refreshing and running the new plan.
 */
export async function runRollover(plan: RolloverPlan, api: RolloverApi, onProgress: (p: RolloverProgress) => void) {
  const total = rolloverStepCount(plan)
  let done = 0
  async function step<T>(current: string, action: () => Promise<T>): Promise<T> {
    onProgress({ done, total, current })
    try {
      const result = await action()
      done += 1
      onProgress({ done, total, current })
      return result
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : 'The request failed.'
      throw new Error(`${current}: ${reason}`)
    }
  }
  const year =
    plan.year.existing ??
    (await step(`Academic year ${plan.year.create.name}`, () =>
      api.createYear({ ...plan.year.create, is_current: false, is_active: true }),
    ))
  const termIds = new Map<number, string>()
  for (const term of plan.terms) {
    const record =
      term.existing ??
      (await step(`Term ${term.create.name}`, () =>
        api.createTerm({ ...term.create, academic_year_id: year.academic_year_id, is_current: false, is_active: true }),
      ))
    termIds.set(term.number, record.semester_id)
  }
  const stageIds = new Map<string, string>()
  for (const section of plan.sections) {
    const key = `${section.programId}:${section.stageNumber}`
    let stageId = section.stageId ?? stageIds.get(key)
    if (!stageId) {
      const stage = await step(`Semester ${section.stageNumber}`, () =>
        api.createStage({
          program_id: section.programId,
          semester_number: section.stageNumber,
          name: `Semester ${section.stageNumber}`,
          code: `SEM-${section.stageNumber}`,
          is_active: true,
        }),
      )
      stageId = stage.program_semester_id
      stageIds.set(key, stageId)
    }
    const label = `${section.batchLabel} · ${section.section.name}`
    const sectionId =
      section.existingSectionId ??
      (
        await step(label, () =>
          api.createSection({
            ...section.section,
            admission_cohort_id: section.batchId,
            program_semester_id: stageId,
            semester_id: termIds.get(section.termNumber)!,
            is_active: true,
          }),
        )
      ).academic_section_id
    for (const subject of section.subjects)
      await step(`${label} subjects`, () =>
        api.createOffering({
          academic_section_id: sectionId,
          curriculum_subject_id: subject.curriculum_subject_id,
          capacity: null,
          is_active: true,
        }),
      )
  }
  return { done, total }
}

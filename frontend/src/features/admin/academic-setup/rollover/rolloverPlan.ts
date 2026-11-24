import type { AcademicCatalogue, AcademicYear, Semester } from '../../../../types/academicSetup.ts'
import type { CurriculumSubject, StructureCatalogue } from '../../../../types/academicStructure.ts'

/** Adds one year to a YYYY-MM-DD date; 29 February becomes 28 February. */
export function nextYearDate(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  const leapDay = month === 2 && day === 29
  return `${year + 1}-${String(month).padStart(2, '0')}-${leapDay ? '28' : String(day).padStart(2, '0')}`
}

/** Moves every 2- or 4-digit year in a label forward: "2026 - 2027" → "2027 - 2028", "ODD26" → "ODD27". */
export function nextYearLabel(label: string): string {
  return label.replace(/(?<!\d)(\d{4}|\d{2})(?!\d)/g, (run) => String(Number(run) + 1).padStart(run.length, '0'))
}

export interface PlannedTerm {
  number: number
  existing?: Semester
  create: { name: string; code: string; semester_number: number; start_date: string; end_date: string }
}
export interface PlannedSection {
  key: string
  batchId: string
  batchLabel: string
  programId: string
  stageNumber: number
  stageId?: string
  termNumber: number
  existingSectionId?: string
  section: { name: string; code: string; capacity: number | null; description: string | null }
  /** Curriculum subjects of the new semester that this section does not offer yet. */
  subjects: CurriculumSubject[]
}
export interface RolloverPlan {
  source: AcademicYear
  year: { existing?: AcademicYear; create: { name: string; code: string; start_date: string; end_date: string } }
  terms: PlannedTerm[]
  sections: PlannedSection[]
  skipped: { label: string; reason: string }[]
}

export function planRollover(
  sourceYearId: string,
  catalogue: AcademicCatalogue,
  structure: StructureCatalogue,
): RolloverPlan | undefined {
  const years = catalogue.records.academic_years ?? []
  const source = years.find((item) => item.academic_year_id === sourceYearId)
  if (!source) return undefined
  const start = nextYearDate(source.start_date)
  const existingYear = years.find((item) => item.start_date === start)
  const allTerms = catalogue.records.semesters ?? []
  const sourceTerms = allTerms
    .filter((term) => term.academic_year_id === source.academic_year_id && term.is_active)
    .sort((a, b) => a.semester_number - b.semester_number)
  const terms: PlannedTerm[] = sourceTerms.map((term) => ({
    number: term.semester_number,
    existing: existingYear
      ? allTerms.find(
          (t) => t.academic_year_id === existingYear.academic_year_id && t.semester_number === term.semester_number,
        )
      : undefined,
    create: {
      name: nextYearLabel(term.name),
      code: nextYearLabel(term.code),
      semester_number: term.semester_number,
      start_date: nextYearDate(term.start_date),
      end_date: nextYearDate(term.end_date),
    },
  }))
  const step = sourceTerms.length
  const records = structure.records
  const stages = records.program_semesters ?? []
  const sections = records.academic_sections ?? []
  const offered = records.academic_offerings ?? []
  const planned: PlannedSection[] = []
  const skipped: RolloverPlan['skipped'] = []
  for (const section of sections) {
    const sourceTerm = sourceTerms.find((term) => term.semester_id === section.semester_id)
    if (!sourceTerm || !section.is_active) continue
    const batch = records.admission_cohorts?.find((item) => item.admission_cohort_id === section.admission_cohort_id)
    if (!batch || batch.status !== 'active' || !batch.is_active) continue
    const stage = stages.find((item) => item.program_semester_id === section.program_semester_id)
    const curriculum = records.curriculum_versions?.find((v) => v.curriculum_version_id === batch.curriculum_version_id)
    if (!stage || !curriculum) continue
    const label = `${batch.name} · ${section.name}`
    const stageNumber = stage.semester_number + step
    const term = terms.find((item) => item.number === sourceTerm.semester_number)!
    if (Number(term.create.end_date.slice(0, 4)) > batch.end_year) {
      skipped.push({ label, reason: `The batch ends in ${batch.end_year}.` })
      continue
    }
    if (stageNumber > curriculum.total_semesters) {
      skipped.push({ label, reason: `The curriculum ends at Semester ${curriculum.total_semesters}.` })
      continue
    }
    const target = stages.find((item) => item.program_id === batch.program_id && item.semester_number === stageNumber)
    const existing = target
      ? sections.find(
          (item) =>
            item.admission_cohort_id === batch.admission_cohort_id &&
            item.program_semester_id === target.program_semester_id &&
            item.code.trim().toLowerCase() === section.code.trim().toLowerCase(),
        )
      : undefined
    const already = new Set(
      offered
        .filter((item) => item.academic_section_id === existing?.academic_section_id)
        .map((o) => o.curriculum_subject_id),
    )
    const subjects = (records.curriculum_subjects ?? []).filter(
      (item) =>
        item.is_active &&
        item.curriculum_version_id === curriculum.curriculum_version_id &&
        item.program_semester_id === target?.program_semester_id &&
        !already.has(item.curriculum_subject_id),
    )
    if (existing && !subjects.length) continue
    planned.push({
      key: `${batch.admission_cohort_id}:${stageNumber}:${section.code.toLowerCase()}`,
      batchId: batch.admission_cohort_id,
      batchLabel: batch.name,
      programId: batch.program_id,
      stageNumber,
      stageId: target?.program_semester_id,
      termNumber: sourceTerm.semester_number,
      existingSectionId: existing?.academic_section_id,
      section: {
        name: section.name.replace(`Semester ${stage.semester_number}`, `Semester ${stageNumber}`),
        code: section.code,
        capacity: section.capacity,
        description: section.description,
      },
      subjects,
    })
  }
  return {
    source,
    year: {
      existing: existingYear,
      create: {
        name: nextYearLabel(source.name),
        code: nextYearLabel(source.code),
        start_date: start,
        end_date: nextYearDate(source.end_date),
      },
    },
    terms,
    sections: planned,
    skipped,
  }
}

/** True when the plan still has something to create. */
export function planHasWork(plan: RolloverPlan) {
  return !plan.year.existing || plan.terms.some((term) => !term.existing) || plan.sections.length > 0
}

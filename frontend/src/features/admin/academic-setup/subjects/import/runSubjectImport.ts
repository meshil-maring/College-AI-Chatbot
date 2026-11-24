import type { AcademicCreateMap, Course } from '../../../../../types/academicSetup.ts'
import type { CurriculumSubject, ProgramSemester, StructureCreateMap } from '../../../../../types/academicStructure.ts'
import type { SubjectImportRow } from './subjectImportModel.ts'

export type RowStatus = 'done' | 'failed'
export interface RowResult {
  status: RowStatus
  courseId?: string
  message?: string
}

export interface ImportApi {
  createCourse: (payload: AcademicCreateMap['courses']) => Promise<Course>
  createStage: (payload: StructureCreateMap['program_semesters']) => Promise<ProgramSemester>
  createMapping: (payload: StructureCreateMap['curriculum_subjects']) => Promise<CurriculumSubject>
}

export interface ImportTarget {
  departmentId: string
  /** Draft curriculum to place subjects in; rows without a semester only create subjects. */
  curriculum?: { curriculum_version_id: string; program_id: string }
  stages: ProgramSemester[]
  mappings: CurriculumSubject[]
}

/**
 * Creates subjects (and curriculum placements) row by row. Rows already done in
 * `previous` are skipped, so a retry only repeats what failed, and every row
 * reuses existing subjects, semesters and placements instead of duplicating them.
 */
export async function runSubjectImport(
  rows: SubjectImportRow[],
  target: ImportTarget,
  api: ImportApi,
  previous: Map<number, RowResult>,
  onProgress: (results: Map<number, RowResult>) => void,
): Promise<Map<number, RowResult>> {
  const results = new Map(previous)
  const stages = new Map(target.stages.map((stage) => [stage.semester_number, stage.program_semester_id]))
  const mapped = new Set(target.mappings.map((mapping) => mapping.course_id))
  for (const row of rows) {
    if (row.errors.length || results.get(row.sourceRow)?.status === 'done') continue
    let courseId = results.get(row.sourceRow)?.courseId ?? row.existingCourseId
    try {
      if (!courseId) {
        const course = await api.createCourse({
          department_id: target.departmentId,
          name: row.name,
          code: row.code,
          description: row.description,
          credits: row.credits,
          lecture_hours: row.lecture_hours,
          tutorial_hours: row.tutorial_hours,
          practical_hours: row.practical_hours,
          is_active: true,
        })
        courseId = course.course_id
      }
      if (target.curriculum && row.semester !== null && !mapped.has(courseId)) {
        let stageId = stages.get(row.semester)
        if (!stageId) {
          const stage = await api.createStage({
            program_id: target.curriculum.program_id,
            semester_number: row.semester,
            name: `Semester ${row.semester}`,
            code: `SEM-${row.semester}`,
            is_active: true,
          })
          stageId = stage.program_semester_id
          stages.set(row.semester, stageId)
        }
        await api.createMapping({
          curriculum_version_id: target.curriculum.curriculum_version_id,
          program_semester_id: stageId,
          course_id: courseId,
          course_type: row.course_type,
          is_required: row.is_required,
          is_active: true,
        })
        mapped.add(courseId)
      }
      results.set(row.sourceRow, { status: 'done', courseId })
    } catch (cause) {
      results.set(row.sourceRow, {
        status: 'failed',
        courseId,
        message: cause instanceof Error ? cause.message : 'Could not save this row.',
      })
    }
    onProgress(new Map(results))
  }
  return results
}

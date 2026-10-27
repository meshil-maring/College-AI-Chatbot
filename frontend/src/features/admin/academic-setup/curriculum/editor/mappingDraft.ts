import type { CourseType, ProgramCourse } from '../../../../../types/academicSetup.ts'
import type { CurriculumState } from '../useCurriculum.ts'
import { COURSE_TYPE_LABELS } from '../../forms/academicCourseTypes.ts'

export interface MappingDraft {
  program_id: string
  course_id: string
  semester_id: string
  course_type: CourseType
  is_required: boolean
  is_active: boolean
}
export type MappingErrors = Partial<Record<keyof MappingDraft, string>>
export function mappingDraft(programId = '', semesterId = '', link?: ProgramCourse): MappingDraft {
  return {
    program_id: link?.program_id ?? programId,
    course_id: link?.course_id ?? '',
    semester_id: link ? (link.semester_id ?? '') : semesterId,
    course_type: link?.course_type ?? 'core',
    is_required: link?.is_required ?? true,
    is_active: link?.is_active ?? true,
  }
}
export function validateMapping(draft: MappingDraft, state: CurriculumState, editing: boolean): MappingErrors {
  const errors: MappingErrors = {}
  if (!draft.course_id) errors.course_id = 'Select a subject.'
  else if (!editing && !state.parents?.courses.has(draft.course_id))
    errors.course_id = 'Select an available active subject.'
  if (!editing && !state.parents?.programs.has(draft.program_id))
    errors.program_id = 'An available active program is required.'
  if (!editing && draft.semester_id && !state.parents?.semesters.has(draft.semester_id))
    errors.semester_id = 'Select an available active academic term.'
  if (!Object.hasOwn(COURSE_TYPE_LABELS, draft.course_type)) errors.course_type = 'Select a subject type.'
  return errors
}

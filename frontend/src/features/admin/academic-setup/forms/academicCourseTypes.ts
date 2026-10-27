import type { CourseType } from '../../../../types/academicSetup.ts'

export const COURSE_TYPE_LABELS: Record<CourseType, string> = {
  core: 'Core',
  elective: 'Elective',
  open_elective: 'Open Elective',
  skill: 'Skill',
  project: 'Project',
}

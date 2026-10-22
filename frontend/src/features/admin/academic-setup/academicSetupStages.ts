import type { AcademicEntity } from '../../../types/academicSetup.ts'

export const ACADEMIC_STAGES = [
  {
    key: 'college',
    title: 'College basics',
    description: 'Add departments, their degree programs, and admission batches.',
    entities: ['departments', 'programs', 'batches'],
  },
  {
    key: 'calendar',
    title: 'Calendar',
    description: 'Set academic years and the dated teaching terms within each year.',
    entities: ['academic_years', 'semesters'],
  },
  {
    key: 'subjects',
    title: 'Subjects',
    description: 'Create each subject once. Classify it when adding it to a curriculum.',
    entities: ['courses'],
  },
  {
    key: 'curricula',
    title: 'Curricula & packages',
    description: 'Name a curriculum, add semester subjects, then build complete subject packages.',
  },
  {
    key: 'classes',
    title: 'Classes',
    description: 'Connect a curriculum to a batch and teaching term, then prepare its subject teaching groups.',
  },
  {
    key: 'assignments',
    title: 'Assignments',
    description: 'Place students in classes, assign complete packages, and review later change requests.',
  },
] as const

export type AcademicStage = (typeof ACADEMIC_STAGES)[number]['key']

export function stageForEntity(entity: AcademicEntity): AcademicStage | undefined {
  return ACADEMIC_STAGES.find(
    (stage) => 'entities' in stage && (stage.entities as readonly AcademicEntity[]).includes(entity),
  )?.key
}

export const FOUNDATION_LABELS: Partial<Record<AcademicEntity, string>> = {
  departments: 'Departments',
  programs: 'Degree programs',
  batches: 'Admission batches',
  academic_years: 'Academic years',
  semesters: 'Teaching terms',
  courses: 'Subjects',
}

import type { Course, Department } from '../../../../../types/academicSetup.ts'

export interface SubjectDraft {
  name: string
  code: string
  department_id: string
  credits: string
  lecture_hours: string
  tutorial_hours: string
  practical_hours: string
  description: string
  is_active: boolean
}
export type SubjectErrors = Partial<Record<keyof SubjectDraft, string>>
export function subjectDraft(record?: Course): SubjectDraft {
  return {
    name: record?.name ?? '',
    code: record?.code ?? '',
    department_id: record?.department_id ?? '',
    credits: record?.credits == null ? '' : String(record.credits),
    lecture_hours: record ? (record.lecture_hours == null ? '' : String(record.lecture_hours)) : '3',
    tutorial_hours: record ? (record.tutorial_hours == null ? '' : String(record.tutorial_hours)) : '1',
    practical_hours: record ? (record.practical_hours == null ? '' : String(record.practical_hours)) : '0',
    description: record?.description ?? '',
    is_active: record?.is_active ?? true,
  }
}

export function validateSubject(draft: SubjectDraft, departments: Department[], editing: boolean): SubjectErrors {
  const errors: SubjectErrors = {}
  if (!draft.name.trim()) errors.name = 'Enter a subject name.'
  else if (draft.name.trim().length > 160) errors.name = 'Use 160 characters or fewer.'
  if (!draft.code.trim()) errors.code = 'Enter a subject code.'
  else if (draft.code.trim().length > 32) errors.code = 'Use 32 characters or fewer.'
  if (!draft.department_id) errors.department_id = 'Select a department.'
  else if (!editing && !departments.some((item) => item.department_id === draft.department_id && item.is_active))
    errors.department_id = 'Select an available active department.'
  if (draft.credits.trim() && (!Number.isFinite(Number(draft.credits)) || Number(draft.credits) <= 0))
    errors.credits = 'Enter credits greater than zero, or leave blank.'
  for (const field of ['lecture_hours', 'tutorial_hours', 'practical_hours'] as const) {
    if (draft[field].trim() && (!Number.isFinite(Number(draft[field])) || Number(draft[field]) < 0))
      errors[field] = 'Enter zero or a positive number, or leave blank.'
  }
  if (draft.description.trim().length > 2000) errors.description = 'Use 2,000 characters or fewer.'
  return errors
}

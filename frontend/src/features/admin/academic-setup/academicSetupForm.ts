import type { AcademicCreate, AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'

export const ACADEMIC_ENTITIES: readonly AcademicEntity[] = [
  'departments',
  'programs',
  'academic_years',
  'semesters',
  'courses',
]
export const ACADEMIC_LABELS: Record<AcademicEntity, string> = {
  departments: 'Departments',
  programs: 'Programs',
  academic_years: 'Academic years',
  semesters: 'Semesters',
  courses: 'Courses',
}
export const ACADEMIC_SINGULAR: Record<AcademicEntity, string> = {
  departments: 'department',
  programs: 'degree program',
  academic_years: 'academic year',
  semesters: 'semester',
  courses: 'course',
}
export const ACADEMIC_HELP: Record<AcademicEntity, string> = {
  departments: 'Departments own degree programs and reusable courses. Deactivate unused records to retain history.',
  programs:
    'Degree programs, such as B.Tech CSE, belong to a department. Assign their subjects in a curriculum version.',
  academic_years: 'Institution-wide calendar periods. Active years cannot overlap; only one year can be current.',
  semesters: 'Dated terms within an academic year. Each term has a semester number; its dates must fit the year.',
  courses: 'Teaching courses belong to departments, with optional credits and lecture, tutorial and practical hours.',
}
const TEXT_FIELDS = [
  'name',
  'code',
  'description',
  'department_id',
  'academic_year_id',
  'semester_id',
  'semester_number',
  'credits',
  'degree_type',
  'duration_years',
  'total_credits',
  'lecture_hours',
  'tutorial_hours',
  'practical_hours',
  'start_date',
  'end_date',
] as const
export type AcademicTextField = (typeof TEXT_FIELDS)[number]
export type AcademicDraft = Record<AcademicTextField, string> & {
  is_active: boolean
  is_current: boolean
}

export function makeAcademicDraft(record?: AcademicRecord): AcademicDraft {
  const values = record as unknown as Record<string, unknown> | undefined
  return {
    ...Object.fromEntries(TEXT_FIELDS.map((key) => [key, String(values?.[key] ?? '')])),
    is_active: record?.is_active ?? true,
    is_current: Boolean(values?.is_current),
  } as AcademicDraft
}
export function academicRecordId(record: AcademicRecord): string {
  if ('semester_number' in record) return record.semester_id
  if ('degree_type' in record) return record.program_id
  if ('credits' in record) return record.course_id
  if ('academic_year_id' in record) return record.academic_year_id
  return record.department_id
}
export function academicPayload(entity: AcademicEntity, draft: AcademicDraft): AcademicCreate {
  const named = { name: draft.name.trim(), code: draft.code.trim(), is_active: draft.is_active }
  const described = { ...named, description: draft.description.trim() || null }
  const optional = (key: AcademicTextField) => (draft[key].trim() ? Number(draft[key]) : null)
  if (entity === 'departments') return described
  if (entity === 'programs')
    return {
      ...described,
      department_id: draft.department_id,
      degree_type: draft.degree_type.trim(),
      duration_years: Number(draft.duration_years),
      total_credits: optional('total_credits'),
    }
  if (entity === 'academic_years' || entity === 'semesters') {
    const period = { ...named, start_date: draft.start_date, end_date: draft.end_date, is_current: draft.is_current }
    return entity === 'academic_years'
      ? period
      : { ...period, academic_year_id: draft.academic_year_id, semester_number: Number(draft.semester_number) }
  }
  return {
    ...described,
    department_id: draft.department_id,
    credits: optional('credits'),
    lecture_hours: optional('lecture_hours'),
    tutorial_hours: optional('tutorial_hours'),
    practical_hours: optional('practical_hours'),
  }
}
export function academicUpdatePayload(entity: AcademicEntity, draft: AcademicDraft) {
  const payload = { ...academicPayload(entity, draft) } as Record<string, unknown>
  for (const key of ['department_id', 'academic_year_id']) delete payload[key]
  return payload
}
export function academicDraftError(entity: AcademicEntity, draft: AcademicDraft): string | null {
  const payload = academicPayload(entity, draft) as unknown as Record<string, unknown>
  if ('name' in payload && (!draft.name.trim() || !draft.code.trim())) return 'Name and code are required.'
  for (const [key, value] of Object.entries(payload)) {
    if (key.endsWith('_id') && !value) return 'Choose all required parent records.'
    if (typeof value === 'number' && !Number.isFinite(value)) return 'Numeric values must be finite.'
  }
  if (
    (entity === 'academic_years' || entity === 'semesters') &&
    (!draft.start_date || !draft.end_date || draft.end_date <= draft.start_date)
  )
    return 'End date must be after the start date.'
  if (entity === 'programs' && (!draft.degree_type.trim() || Number(draft.duration_years) <= 0))
    return 'Degree type and positive duration are required.'
  if (
    entity === 'semesters' &&
    (!Number.isInteger(Number(draft.semester_number)) || Number(draft.semester_number) <= 0)
  )
    return 'Semester number must be a positive whole number.'
  for (const key of ['credits', 'lecture_hours', 'tutorial_hours', 'practical_hours']) {
    const value = payload[key]
    if (typeof value === 'number' && (value < 0 || (key === 'credits' && value === 0)))
      return 'Credits must be positive; teaching hours cannot be negative.'
  }
  return null
}

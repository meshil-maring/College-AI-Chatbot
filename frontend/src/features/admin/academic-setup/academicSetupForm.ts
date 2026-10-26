import type { AcademicCreate, AcademicEntity, AcademicRecord, CourseType } from '../../../types/academicSetup.ts'

export const ACADEMIC_ENTITIES: readonly AcademicEntity[] = [
  'departments',
  'programs',
  'academic_years',
  'semesters',
  'courses',
  'program_courses',
  'course_offerings',
  'sections',
]
export const ACADEMIC_LABELS: Record<AcademicEntity, string> = {
  departments: 'Departments',
  programs: 'Programs',
  academic_years: 'Academic years',
  semesters: 'Semesters',
  courses: 'Courses',
  program_courses: 'Program courses',
  course_offerings: 'Course offerings',
  sections: 'Sections',
}
export const ACADEMIC_SINGULAR: Record<AcademicEntity, string> = {
  departments: 'department',
  programs: 'degree program',
  academic_years: 'academic year',
  semesters: 'semester',
  courses: 'course',
  program_courses: 'program course',
  course_offerings: 'course offering',
  sections: 'section',
}
export const ACADEMIC_HELP: Record<AcademicEntity, string> = {
  departments: 'Departments own degree programs and reusable courses. Deactivate unused records to retain history.',
  programs:
    'Degree programs, such as B.Tech CSE, belong to a department. Link their teaching courses under Program courses.',
  academic_years: 'Institution-wide calendar periods. Active years cannot overlap; only one year can be current.',
  semesters: 'Dated terms within an academic year. Each term has a semester number; its dates must fit the year.',
  courses: 'Teaching courses belong to departments, with optional credits and lecture, tutorial and practical hours.',
  program_courses:
    'Link a course to a degree program, optionally for a specific semester. Choose its type and whether it is required.',
  course_offerings: 'Offer a linked course to a program during an academic year and semester, with optional capacity.',
  sections: 'Each section belongs to one course offering. Its offering and code remain fixed after creation.',
}
const TEXT_FIELDS = [
  'name',
  'code',
  'description',
  'department_id',
  'program_id',
  'academic_year_id',
  'semester_id',
  'course_id',
  'course_offering_id',
  'semester_number',
  'credits',
  'degree_type',
  'duration_years',
  'total_credits',
  'lecture_hours',
  'tutorial_hours',
  'practical_hours',
  'capacity',
  'course_type',
  'start_date',
  'end_date',
] as const
export type AcademicTextField = (typeof TEXT_FIELDS)[number]
export type AcademicDraft = Record<AcademicTextField, string> & {
  is_active: boolean
  is_current: boolean
  is_required: boolean
}

export function makeAcademicDraft(record?: AcademicRecord): AcademicDraft {
  const values = record as unknown as Record<string, unknown> | undefined
  return {
    ...Object.fromEntries(TEXT_FIELDS.map((key) => [key, String(values?.[key] ?? '')])),
    is_active: record?.is_active ?? true,
    is_current: Boolean(values?.is_current),
    is_required: values?.is_required !== false,
  } as AcademicDraft
}
export function academicRecordId(record: AcademicRecord): string {
  if ('section_id' in record) return record.section_id
  if ('course_offering_id' in record) return record.course_offering_id
  if ('program_course_id' in record) return record.program_course_id
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
  if (entity === 'courses')
    return {
      ...described,
      department_id: draft.department_id,
      credits: optional('credits'),
      lecture_hours: optional('lecture_hours'),
      tutorial_hours: optional('tutorial_hours'),
      practical_hours: optional('practical_hours'),
    }
  if (entity === 'program_courses')
    return {
      program_id: draft.program_id,
      course_id: draft.course_id,
      semester_id: draft.semester_id || null,
      course_type: draft.course_type as CourseType,
      is_required: draft.is_required,
      is_active: draft.is_active,
    }
  if (entity === 'course_offerings')
    return {
      program_id: draft.program_id,
      course_id: draft.course_id,
      academic_year_id: draft.academic_year_id,
      semester_id: draft.semester_id,
      capacity: optional('capacity'),
      is_active: draft.is_active,
    }
  return { ...named, course_offering_id: draft.course_offering_id, capacity: optional('capacity') }
}
export function academicUpdatePayload(entity: AcademicEntity, draft: AcademicDraft) {
  const payload = { ...academicPayload(entity, draft) } as Record<string, unknown>
  for (const key of [
    'department_id',
    'program_id',
    'course_id',
    'academic_year_id',
    'semester_id',
    'course_offering_id',
  ])
    delete payload[key]
  if (entity === 'sections') delete payload.code
  return payload
}
export function academicDraftError(entity: AcademicEntity, draft: AcademicDraft): string | null {
  const payload = academicPayload(entity, draft) as unknown as Record<string, unknown>
  if ('name' in payload && (!draft.name.trim() || !draft.code.trim())) return 'Name and code are required.'
  for (const [key, value] of Object.entries(payload)) {
    if (key.endsWith('_id') && !value && !(entity === 'program_courses' && key === 'semester_id'))
      return 'Choose all required parent records.'
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
  if (
    entity === 'program_courses' &&
    !['core', 'elective', 'open_elective', 'skill', 'project'].includes(draft.course_type)
  )
    return 'Choose a course type.'
  for (const key of ['credits', 'capacity', 'lecture_hours', 'tutorial_hours', 'practical_hours']) {
    const value = payload[key]
    if (typeof value === 'number' && (value < 0 || (['credits', 'capacity'].includes(key) && value === 0)))
      return 'Credits and capacity must be positive; teaching hours cannot be negative.'
  }
  if (typeof payload.capacity === 'number' && !Number.isInteger(payload.capacity))
    return 'Capacity must be a whole number.'
  return null
}

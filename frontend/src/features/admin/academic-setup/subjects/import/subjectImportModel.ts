import type { Course, CourseType } from '../../../../../types/academicSetup.ts'
import { csvCell, normalizeCsvHeader, parseCsv } from '../../../../../lib/csv.ts'

export const SUBJECT_IMPORT_LIMIT = 300

export interface SubjectImportRow {
  sourceRow: number
  code: string
  name: string
  description: string | null
  credits: number | null
  lecture_hours: number | null
  tutorial_hours: number | null
  practical_hours: number | null
  semester: number | null
  course_type: CourseType
  is_required: boolean
  /** Set when the department already has a subject with this code; it is reused, not re-created. */
  existingCourseId?: string
  errors: string[]
}

type Field = Exclude<keyof SubjectImportRow, 'sourceRow' | 'existingCourseId' | 'errors'>
const HEADERS: Record<string, Field> = {
  code: 'code',
  subjectcode: 'code',
  coursecode: 'code',
  name: 'name',
  subjectname: 'name',
  coursename: 'name',
  title: 'name',
  description: 'description',
  credits: 'credits',
  credit: 'credits',
  l: 'lecture_hours',
  lecture: 'lecture_hours',
  lecturehours: 'lecture_hours',
  t: 'tutorial_hours',
  tutorial: 'tutorial_hours',
  tutorialhours: 'tutorial_hours',
  p: 'practical_hours',
  practical: 'practical_hours',
  practicalhours: 'practical_hours',
  semester: 'semester',
  semesternumber: 'semester',
  programsemester: 'semester',
  type: 'course_type',
  subjecttype: 'course_type',
  coursetype: 'course_type',
  required: 'is_required',
  compulsory: 'is_required',
  isrequired: 'is_required',
}
const TYPES: Record<string, CourseType> = {
  core: 'core',
  elective: 'elective',
  openelective: 'open_elective',
  skill: 'skill',
  project: 'project',
}
const YES = new Set(['yes', 'y', 'true', '1', 'required', 'compulsory'])
const NO = new Set(['no', 'n', 'false', '0', 'optional', 'choice'])

export const SUBJECT_TEMPLATE = [
  ['code', 'name', 'credits', 'L', 'T', 'P', 'semester', 'type', 'required', 'description'],
  ['CS101', 'Programming Fundamentals', 4, 3, 1, 2, 1, 'core', 'yes', ''],
  ['CS205', 'Machine Learning', 3, 3, 0, 0, 5, 'elective', 'no', 'Semester 5 elective option'],
]
  .map((row) => row.map(csvCell).join(','))
  .join('\n')

function number(value: string, label: string, errors: string[], positive: boolean): number | null {
  if (!value) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0 || (positive && parsed === 0)) {
    errors.push(`${label} must be ${positive ? 'greater than zero' : 'zero or more'}.`)
    return null
  }
  return parsed
}

/** Reads the file into rows; throws for problems with the file itself. */
export function parseSubjectCsv(text: string): Record<Field, string>[] {
  const [header, ...rows] = parseCsv(text, SUBJECT_IMPORT_LIMIT, 'subject rows')
  if (!header) throw new Error('The file is empty.')
  const columns = header.map((cell) => HEADERS[normalizeCsvHeader(cell)])
  if (!columns.includes('code') || !columns.includes('name'))
    throw new Error('The file needs "code" and "name" columns. Download the template to see the format.')
  if (!rows.length) throw new Error('The file has a header but no subject rows.')
  return rows.map((row) => {
    const values = {} as Record<Field, string>
    columns.forEach((field, index) => {
      if (field && values[field] === undefined) values[field] = (row[index] ?? '').trim()
    })
    return values
  })
}

/** Validates parsed rows against the department's subjects and the chosen curriculum. */
export function validateSubjectRows(
  raw: Record<Field, string>[],
  existing: Course[],
  totalSemesters: number | null,
): SubjectImportRow[] {
  const byCode = new Map(existing.map((course) => [course.code.trim().toLowerCase(), course]))
  const seen = new Map<string, number>()
  return raw.map((values, index) => {
    const errors: string[] = []
    const sourceRow = index + 2
    const code = values.code ?? ''
    const name = values.name ?? ''
    if (!code) errors.push('Code is required.')
    else if (code.length > 32) errors.push('Code must be 32 characters or fewer.')
    if (!name) errors.push('Name is required.')
    else if (name.length > 160) errors.push('Name must be 160 characters or fewer.')
    const key = code.toLowerCase()
    if (code && seen.has(key)) errors.push(`Code is repeated (also on row ${seen.get(key)}).`)
    else if (code) seen.set(key, sourceRow)
    const typeKey = normalizeCsvHeader(values.course_type)
    const course_type = typeKey ? TYPES[typeKey] : 'core'
    if (!course_type) errors.push('Type must be core, elective, open elective, skill or project.')
    const requiredKey = (values.is_required ?? '').toLowerCase()
    const optionalType = course_type === 'elective' || course_type === 'open_elective'
    const is_required = YES.has(requiredKey) ? true : NO.has(requiredKey) ? false : !optionalType
    if (requiredKey && !YES.has(requiredKey) && !NO.has(requiredKey)) errors.push('Required must be yes or no.')
    let semester: number | null = null
    if (values.semester && totalSemesters !== null) {
      semester = Number(values.semester)
      if (!Number.isInteger(semester) || semester < 1 || semester > totalSemesters) {
        errors.push(`Semester must be a whole number from 1 to ${totalSemesters}.`)
        semester = null
      }
    }
    return {
      sourceRow,
      code,
      name,
      description: values.description || null,
      credits: number(values.credits ?? '', 'Credits', errors, true),
      lecture_hours: number(values.lecture_hours ?? '', 'Lecture hours', errors, false),
      tutorial_hours: number(values.tutorial_hours ?? '', 'Tutorial hours', errors, false),
      practical_hours: number(values.practical_hours ?? '', 'Practical hours', errors, false),
      semester,
      course_type: course_type ?? 'core',
      is_required,
      existingCourseId: byCode.get(key)?.course_id,
      errors,
    }
  })
}

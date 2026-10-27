import type { AcademicYear, Semester } from '../../../../../types/academicSetup.ts'

export interface SemesterDraft {
  key: string
  semester_number: number
  start_date: string
  end_date: string
}
export interface CalendarDraft {
  name: string
  code: string
  start_date: string
  end_date: string
  is_active: boolean
  is_current: boolean
  academic_year_id: string
  semester_number: number
  plan: '2' | '3' | 'custom'
  semesters: SemesterDraft[]
}
export type CalendarErrors = Partial<Record<keyof CalendarDraft, string>>
export type CalendarPanel = {
  entity: 'academic_years' | 'semesters'
  mode: 'add' | 'view' | 'edit'
  record?: AcademicYear | Semester
}

export function makeSemesters(start: string, end: string, count: number): SemesterDraft[] {
  const first = Date.parse(`${start}T00:00:00Z`)
  const last = Date.parse(`${end}T00:00:00Z`)
  if (!Number.isFinite(first) || !Number.isFinite(last) || last <= first) return []
  const days = Math.floor((last - first) / 86400000) + 1
  const date = (day: number) => new Date(first + day * 86400000).toISOString().slice(0, 10)
  return Array.from({ length: count }, (_, index) => ({
    key: crypto.randomUUID(),
    semester_number: index + 1,
    start_date: date(Math.floor((days * index) / count)),
    end_date: date(Math.floor((days * (index + 1)) / count) - 1),
  }))
}

export function calendarDraft(record?: AcademicYear | Semester, parent?: AcademicYear): CalendarDraft {
  const year = new Date().getFullYear()
  const start = `${year}-08-01`
  const end = `${year + 1}-07-31`
  return {
    name: record?.name ?? (parent ? '' : `${year} - ${year + 1}`),
    code: record?.code ?? (parent ? '' : `AY${year}`),
    start_date: record?.start_date ?? parent?.start_date ?? start,
    end_date: record?.end_date ?? parent?.end_date ?? end,
    is_active: record?.is_active ?? true,
    is_current: record?.is_current ?? false,
    academic_year_id: record && 'semester_id' in record ? record.academic_year_id : (parent?.academic_year_id ?? ''),
    semester_number: record && 'semester_id' in record ? record.semester_number : 1,
    plan: '2',
    semesters: makeSemesters(start, end, 2),
  }
}

export function validateCalendar(
  draft: CalendarDraft,
  panel: CalendarPanel,
  years: AcademicYear[],
  includeSemesters: boolean,
) {
  const errors: CalendarErrors = {}
  if (!draft.name.trim()) errors.name = 'Enter a name.'
  if (!draft.code.trim()) errors.code = 'Enter a code.'
  if (draft.name.trim().length > 160) errors.name = 'Use at most 160 characters.'
  if (draft.code.trim().length > 32) errors.code = 'Use at most 32 characters.'
  const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value))
  if (!validDate(draft.start_date)) errors.start_date = 'Choose a valid start date.'
  if (!validDate(draft.end_date) || draft.end_date <= draft.start_date)
    errors.end_date = 'End date must be after start date.'
  if (draft.is_current && !draft.is_active) errors.is_current = 'A current period must be active.'
  if (panel.entity === 'semesters') {
    const parent = years.find((item) => item.academic_year_id === draft.academic_year_id)
    if (!parent || (panel.mode === 'add' && !parent.is_active))
      errors.academic_year_id = 'Select an available active academic year.'
    if (!Number.isInteger(draft.semester_number) || draft.semester_number < 1 || draft.semester_number > 2147483647)
      errors.semester_number = 'Enter a positive whole semester number.'
    if (parent && (draft.start_date < parent.start_date || draft.end_date > parent.end_date))
      errors.end_date = 'Semester dates must fall within the academic year.'
  }
  if (includeSemesters) {
    if (draft.semesters.length && !draft.is_active)
      errors.is_active = 'Activate the academic year before adding semesters.'
    const numbers = new Set<number>()
    for (const semester of draft.semesters) {
      if (
        !Number.isInteger(semester.semester_number) ||
        semester.semester_number < 1 ||
        semester.semester_number > 2147483647 ||
        numbers.has(semester.semester_number) ||
        !validDate(semester.start_date) ||
        !validDate(semester.end_date) ||
        semester.start_date < draft.start_date ||
        semester.end_date > draft.end_date ||
        semester.end_date <= semester.start_date
      ) {
        errors.semesters = 'Use unique positive semester numbers and valid dates within the academic year.'
      }
      numbers.add(semester.semester_number)
    }
  }
  return errors
}

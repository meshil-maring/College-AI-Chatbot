/** Pure helpers for the Quick Setup flow. */

export const QUICK_SETUP_STEPS = [
  { id: 'department', title: 'Department' },
  { id: 'program', title: 'Program' },
  { id: 'calendar', title: 'Calendar' },
  { id: 'curriculum', title: 'Curriculum' },
  { id: 'subjects', title: 'Subjects' },
  { id: 'publish', title: 'Publish' },
  { id: 'batch', title: 'Batch & sections' },
] as const
/** 'done' is the completion screen after the last step. */
export type QuickSetupStep = (typeof QUICK_SETUP_STEPS)[number]['id'] | 'done'

function iso(date: Date) {
  return date.toISOString().slice(0, 10)
}

/** Splits an academic year into equal, back-to-back terms named "Term 1", "Term 2", … */
export function splitYearIntoTerms(start: string, end: string, count: number) {
  const first = Date.parse(`${start}T00:00:00Z`)
  const last = Date.parse(`${end}T00:00:00Z`)
  if (!Number.isFinite(first) || !Number.isFinite(last) || last <= first || count < 1) return []
  const days = Math.round((last - first) / 86_400_000) + 1
  return Array.from({ length: count }, (_, index) => {
    const from = first + Math.floor((days * index) / count) * 86_400_000
    const to = first + (Math.floor((days * (index + 1)) / count) - 1) * 86_400_000
    return {
      name: `Term ${index + 1}`,
      code: `T${index + 1}`,
      semester_number: index + 1,
      start_date: iso(new Date(from)),
      end_date: iso(new Date(to)),
    }
  })
}

/** Two program semesters per year of study, as curricula default to. */
export function semesterCount(durationYears: number) {
  return Math.min(32, Math.max(1, Math.ceil(durationYears * 2)))
}

/** A batch starts in its intake year and runs for the program's whole duration. */
export function batchYears(intakeStart: string, durationYears: number) {
  const start = Number(intakeStart.slice(0, 4))
  return { start_year: start, end_year: start + Math.ceil(durationYears) }
}

/** Section letters A, B, C, … for the requested number of sections. */
export function sectionLetters(count: number) {
  return Array.from({ length: Math.min(26, Math.max(1, count)) }, (_, index) => String.fromCharCode(65 + index))
}

/** Blank when valid; otherwise the first problem with a name/code pair. */
export function nameCodeError(name: string, code: string) {
  if (!name.trim()) return 'Enter a name.'
  if (!code.trim()) return 'Enter a code.'
  if (code.trim().length > 32) return 'Use a code of 32 characters or fewer.'
  return ''
}

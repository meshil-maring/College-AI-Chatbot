export type BatchStatus = 'active' | 'completed' | 'inactive'
export type BatchSort = 'year-desc' | 'year-asc' | 'name-asc' | 'name-desc'
export interface BatchDraft {
  name: string
  code: string
  programId: string
  curriculumId: string
  academicYear: string
  startYear: string
  endYear: string
  expectedCount: string
  description: string
  status: BatchStatus
}
export interface BatchRecord extends BatchDraft {
  id: string
  studentCount: number | null
}
export interface BatchProgram {
  id: string
  name: string
  code: string
  duration: number
  color: string
}
export interface BatchCurriculum {
  id: string
  programId: string
  version: string
}
export const BATCH_PAGE_SIZE = 10
export const batchStatuses: { value: BatchStatus; label: string; description: string }[] = [
  { value: 'active', label: 'Active', description: 'Batch is active for student enrollment' },
  { value: 'completed', label: 'Completed', description: 'Batch has completed its academic period' },
  { value: 'inactive', label: 'Inactive', description: 'Temporarily disabled' },
]
export function emptyBatch(): BatchDraft {
  return {
    name: '',
    code: '',
    programId: '',
    curriculumId: '',
    academicYear: '',
    startYear: '',
    endYear: '',
    expectedCount: '',
    description: '',
    status: 'active',
  }
}
export interface BatchYear {
  academic_year_id: string
  start_date: string
}
/** A batch starts in the calendar year its intake academic year starts. */
export function intakeStartYear(yearId: string, years: BatchYear[]) {
  const year = years.find((item) => item.academic_year_id === yearId)
  return year ? year.start_date.slice(0, 4) : ''
}
/** Longest span allowed for the program; shorter spans suit lateral-entry batches. */
export function batchSpan(programId: string, programs: BatchProgram[]) {
  const duration = programs.find((item) => item.id === programId)?.duration
  return duration && duration > 0 ? Math.ceil(duration) : undefined
}
/** Fill the start year, end year and sole published curriculum from earlier choices. */
export function deriveBatch(
  draft: BatchDraft,
  changed: keyof BatchDraft,
  programs: BatchProgram[],
  curricula: (BatchCurriculum & { active?: boolean })[],
  years: BatchYear[],
): BatchDraft {
  const next = { ...draft }
  if (changed === 'programId') {
    const published = curricula.filter((item) => item.programId === next.programId && item.active !== false)
    next.curriculumId = published.length === 1 ? published[0].id : ''
  }
  if (changed === 'academicYear') next.startYear = intakeStartYear(next.academicYear, years)
  if ((changed === 'programId' || changed === 'academicYear') && next.startYear) {
    const span = batchSpan(next.programId, programs)
    if (span) next.endYear = String(Number(next.startYear) + span)
  }
  return next
}
export function batchDraft(record: BatchRecord): BatchDraft {
  const { id: _id, studentCount: _students, ...draft } = record
  return draft
}
export function filterBatches(
  records: BatchRecord[],
  programs: BatchProgram[],
  filters: { search: string; program: string; year: string; status: string; sort: BatchSort },
) {
  const search = filters.search.trim().toLowerCase()
  return records
    .filter((record) => {
      const program = programs.find((item) => item.id === record.programId)
      return (
        (!search || `${record.name} ${record.code} ${program?.name} ${program?.code}`.toLowerCase().includes(search)) &&
        (!filters.program || record.programId === filters.program) &&
        (!filters.year || record.academicYear === filters.year) &&
        (!filters.status || record.status === filters.status)
      )
    })
    .sort((a, b) => {
      if (filters.sort === 'name-asc') return a.name.localeCompare(b.name)
      if (filters.sort === 'name-desc') return b.name.localeCompare(a.name)
      const difference = Number(a.startYear) - Number(b.startYear)
      return filters.sort === 'year-asc' ? difference : -difference
    })
}
export function validateBatch(
  draft: BatchDraft,
  records: BatchRecord[],
  programs: BatchProgram[],
  curricula: BatchCurriculum[],
  id?: string,
  years: BatchYear[] = [],
) {
  if (!draft.name.trim() || !draft.code.trim()) return 'Enter a batch name and code.'
  if (!id && !programs.some((item) => item.id === draft.programId)) return 'Select a program.'
  if (!id && !curricula.some((item) => item.id === draft.curriculumId && item.programId === draft.programId))
    return 'Select a published curriculum version for this program.'
  if (!draft.academicYear) return 'Select an academic year.'
  const start = Number(draft.startYear)
  const end = Number(draft.endYear)
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1900 || end > 2200 || end <= start)
    return 'End year must be later than start year, between 1900 and 2200.'
  if (!id) {
    const intake = intakeStartYear(draft.academicYear, years)
    if (intake && Number(intake) !== start) return `Start year must be ${intake}, when the intake academic year starts.`
    const span = batchSpan(draft.programId, programs)
    if (span && end - start > span) return `End year cannot be later than ${start + span} for this program's duration.`
  }
  if (draft.expectedCount && (!/^\d+$/.test(draft.expectedCount) || !Number.isSafeInteger(Number(draft.expectedCount))))
    return 'Expected student count must be a nonnegative whole number.'
  if (records.some((item) => item.id !== id && item.code.toLowerCase() === draft.code.trim().toLowerCase()))
    return 'A batch with this code already exists.'
  return undefined
}

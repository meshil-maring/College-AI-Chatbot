import { createAcademicRecord, updateAcademicRecord } from '../../../../../services/admin/academics.ts'
import type { AcademicYear, Semester } from '../../../../../types/academicSetup.ts'
import type { CalendarDraft, CalendarPanel } from './calendarDraft.ts'

export interface CalendarProgress {
  year?: AcademicYear
  completed: number
}
interface Options {
  token: string
  institutionId: string
  panel: CalendarPanel
  draft: CalendarDraft
  includeSemesters: boolean
  progress: CalendarProgress
  isAvailable: () => boolean
  onProgress: (progress: CalendarProgress) => void
}

/** Checkpoint each successful request so a partial failure never repeats a saved record. */
export async function saveCalendar(options: Options) {
  const { token, institutionId, panel, draft, progress, isAvailable, onProgress } = options
  function checkAvailable() {
    if (!isAvailable()) throw new Error('Calendar changes are unavailable. Refresh and try again.')
  }
  function verify(record: AcademicYear | Semester) {
    if (record.institution_id !== institutionId)
      throw new Error('The saved record could not be verified for this institution.')
  }
  checkAvailable()
  const payload = {
    name: draft.name.trim(),
    code: draft.code.trim(),
    start_date: draft.start_date,
    end_date: draft.end_date,
    is_active: draft.is_active,
    is_current: draft.is_current,
  }
  if (panel.entity === 'semesters') {
    const changes = { ...payload, semester_number: draft.semester_number }
    const result =
      panel.mode === 'edit' && panel.record && 'semester_id' in panel.record
        ? await updateAcademicRecord(token, 'semesters', panel.record.semester_id, changes)
        : await createAcademicRecord(token, 'semesters', { ...changes, academic_year_id: draft.academic_year_id })
    verify(result)
    return
  }
  if (panel.mode === 'edit' && panel.record && 'academic_year_id' in panel.record) {
    verify(await updateAcademicRecord(token, 'academic_years', panel.record.academic_year_id, payload))
    return
  }
  let year = progress.year
  if (!year) {
    year = await createAcademicRecord(token, 'academic_years', payload)
    verify(year)
    onProgress({ year, completed: 0 })
  }
  if (!options.includeSemesters) return
  for (let index = progress.completed; index < draft.semesters.length; index++) {
    checkAvailable()
    const semester = draft.semesters[index]
    const result = await createAcademicRecord(token, 'semesters', {
      academic_year_id: year.academic_year_id,
      name: `Semester ${semester.semester_number}`,
      code: `S${semester.semester_number}`,
      semester_number: semester.semester_number,
      start_date: semester.start_date,
      end_date: semester.end_date,
      is_active: true,
      is_current: false,
    })
    verify(result)
    if (result.academic_year_id !== year.academic_year_id)
      throw new Error('The saved semester has an unexpected academic year.')
    onProgress({ year, completed: index + 1 })
  }
}

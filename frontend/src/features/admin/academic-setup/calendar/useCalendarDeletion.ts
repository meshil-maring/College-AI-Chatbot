import { useAcademicDeletion } from '../deletion/useAcademicDeletion.ts'
import type { CalendarPeriod } from './calendarModel.ts'
import type { CalendarContext, CalendarState } from './useCalendar.ts'

export function useCalendarDeletion(context: CalendarContext, state: CalendarState, editing: boolean) {
  const options = {
    ...context,
    catalogue: state.catalogue,
    busy: state.busy || editing,
    refresh: state.query.refetch,
  }
  const years = useAcademicDeletion({ ...options, entity: 'academic_years' })
  const semesters = useAcademicDeletion({ ...options, entity: 'semesters' })
  const saving = years.saving || semesters.saving
  function forRecord(record: CalendarPeriod) {
    return 'semester_id' in record ? semesters : years
  }
  return {
    saving,
    active: years.record ? years : semesters.record ? semesters : null,
    notice: years.notice || semesters.notice,
    canManage: (record: CalendarPeriod) => forRecord(record).canManage,
    open: (record: CalendarPeriod) => {
      if (saving) return
      years.close()
      semesters.close()
      years.clearNotice()
      semesters.clearNotice()
      forRecord(record).open(record)
    },
  }
}
export type CalendarDeletion = ReturnType<typeof useCalendarDeletion>

import type { AcademicYear, Semester } from '../../../../types/academicSetup.ts'

export type CalendarPeriod = AcademicYear | Semester
export type CalendarTab = 'years' | 'semesters' | 'dates' | 'timeline'
export type CalendarStatus = 'all' | 'active' | 'upcoming' | 'completed' | 'inactive'
export type CalendarSort = 'newest' | 'oldest' | 'name'
export const CALENDAR_PAGE_SIZE = 6
export const calendarTabs: { id: CalendarTab; label: string }[] = [
  { id: 'years', label: 'Academic Years' },
  { id: 'semesters', label: 'Semesters' },
  { id: 'dates', label: 'Important Dates' },
  { id: 'timeline', label: 'Overview Timeline' },
]

export function localDate() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export function periodStatus(period: CalendarPeriod, today = localDate()): Exclude<CalendarStatus, 'all'> {
  if (!period.is_active) return 'inactive'
  if (period.is_current) return 'active'
  if (period.end_date < today) return 'completed'
  return period.start_date > today ? 'upcoming' : 'active'
}

export function formatCalendarDate(value: string) {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00Z`),
  )
}

export function semesterType(number: number) {
  return number % 2 ? 'Odd' : 'Even'
}

export function filterPeriods<T extends CalendarPeriod>(
  periods: T[],
  search: string,
  status: CalendarStatus,
  sort: CalendarSort,
) {
  const term = search.trim().toLowerCase()
  return periods
    .filter(
      (period) =>
        `${period.name} ${period.code}`.toLowerCase().includes(term) &&
        (status === 'all' || periodStatus(period) === status),
    )
    .sort((a, b) =>
      sort === 'name'
        ? a.name.localeCompare(b.name)
        : sort === 'oldest'
          ? a.start_date.localeCompare(b.start_date)
          : b.start_date.localeCompare(a.start_date),
    )
}

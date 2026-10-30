import type { CalendarTab } from '../calendar/calendarModel.ts'
import type { AcademicPage } from '../overview/academicOverviewModel.ts'

export const calendarDestinations: Record<CalendarTab, AcademicPage> = {
  years: 'years',
  semesters: 'terms',
  dates: 'calendar-dates',
  timeline: 'calendar-timeline',
}

export function calendarTabFor(page: AcademicPage): CalendarTab | undefined {
  if (page === 'calendar') return 'years'
  return (Object.keys(calendarDestinations) as CalendarTab[]).find((tab) => calendarDestinations[tab] === page)
}

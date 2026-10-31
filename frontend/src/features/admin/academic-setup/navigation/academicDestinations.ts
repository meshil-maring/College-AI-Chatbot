import { ClipboardList, Database, History, CalendarDays, CalendarRange } from 'lucide-react'
import type { AcademicArea } from '../overview/academicOverviewModel.ts'

export const academicDestinations: readonly AcademicArea[] = [
  {
    page: 'calendar-dates',
    title: 'Important Dates',
    icon: CalendarDays,
    description: 'Review the dates configured in your academic calendar.',
    action: 'View Important Dates',
    note: 'Dates come from your academic years and teaching terms.',
  },
  {
    page: 'calendar-timeline',
    title: 'Overview Timeline',
    icon: CalendarRange,
    description: 'Explore academic years and teaching terms on the calendar timeline.',
    action: 'View Calendar Timeline',
    note: 'A dated overview of the academic calendar.',
  },
  {
    page: 'curriculum-existing',
    title: 'Existing Program Mappings',
    icon: Database,
    description: 'Review the separately retained program and dated-term subject mappings.',
    action: 'Open Existing Program Mappings',
    note: 'These mappings are separate from versioned curricula.',
  },
  {
    page: 'curriculum-history',
    title: 'Version History',
    icon: History,
    description: 'Review the published curriculum versions retained by admission batches.',
    action: 'View Version History',
    note: 'Published mappings and options remain preserved.',
  },
  {
    page: 'enrollments',
    title: 'Student Enrollment',
    icon: ClipboardList,
    description: 'Assign approved students to a section so they can register their semester subjects.',
    action: 'Manage Student Enrollment',
    note: 'Students choose their subject options in Semester Registration.',
  },
]

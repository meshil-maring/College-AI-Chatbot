import { BookOpenText, ClipboardList, History, CalendarDays, CalendarRange, Wand2 } from 'lucide-react'
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
  {
    page: 'guide',
    title: 'User Guide',
    icon: BookOpenText,
    description: 'Step-by-step instructions for setting up departments, curricula, batches and enrollment.',
    action: 'Open User Guide',
    note: 'A worked example from departments to student enrollment.',
  },
  {
    page: 'quick-setup',
    title: 'Quick Setup',
    icon: Wand2,
    description: 'Set up a program step by step, from department to first-year sections.',
    action: 'Start Quick Setup',
    note: 'Each step saves before moving on and can reuse existing records.',
  },
]

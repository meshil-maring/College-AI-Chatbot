import type { AcademicPage } from '../overview/academicOverviewModel.ts'

export const academicJourney = [
  {
    id: 'foundation',
    title: 'Foundations',
    page: 'departments',
    pages: [
      'departments',
      'programs',
      'calendar',
      'years',
      'terms',
      'calendar-dates',
      'calendar-timeline',
      'program-semesters',
      'subjects',
    ],
    description: 'Set up programs, teaching dates, study semesters and reusable subjects.',
  },
  {
    id: 'curriculum',
    title: 'Curriculum',
    page: 'curriculum-versions',
    pages: [
      'curriculum',
      'curriculum-versions',
      'curriculum-subjects',
      'curriculum-options',
      'curriculum-history',
      'curriculum-existing',
    ],
    description: 'Map subjects, define options and publish the curriculum.',
  },
  {
    id: 'batches',
    title: 'Batches',
    page: 'cohorts',
    pages: ['cohorts'],
    description: 'Assign a published curriculum to an admission intake.',
  },
  {
    id: 'delivery',
    title: 'Classes & subjects',
    page: 'sections',
    pages: ['sections', 'offerings'],
    description: 'Create term-specific sections and offer their curriculum subjects.',
  },
  {
    id: 'enrollment',
    title: 'Student enrollment',
    page: 'enrollments',
    pages: ['enrollments'],
    description: 'Assign students to sections; students then register their subject options.',
  },
] as const

interface Guidance {
  description: string
  next: AcademicPage
  action: string
}
const guidance: Partial<Record<AcademicPage, Guidance>> = {
  departments: {
    description: 'Create the department that will own your degree programs and subjects.',
    next: 'programs',
    action: 'Set up programs',
  },
  programs: {
    description: 'Define each degree before preparing its academic calendar and curriculum.',
    next: 'years',
    action: 'Configure academic calendar',
  },
  calendar: {
    description: 'Academic years and terms describe when teaching happens.',
    next: 'program-semesters',
    action: 'Define program semesters',
  },
  years: {
    description: 'Add the dated teaching terms within each academic year.',
    next: 'terms',
    action: 'Configure academic terms',
  },
  terms: {
    description: 'Keep teaching dates separate from the study stages of a degree.',
    next: 'program-semesters',
    action: 'Define program semesters',
  },
  'program-semesters': {
    description: 'Define the study stages, such as Semester 1–8, then prepare the reusable subject catalogue.',
    next: 'subjects',
    action: 'Manage subjects',
  },
  subjects: {
    description: 'Subjects are reusable. Assign them to specific semesters through Curriculum Subjects.',
    next: 'curriculum-versions',
    action: 'Prepare a curriculum',
  },
  curriculum: {
    description: 'Create a draft, map its semester subjects, and review any subject options before publishing.',
    next: 'curriculum-subjects',
    action: 'Map semester subjects',
  },
  'curriculum-versions': {
    description: 'Finish subject mappings and options before publishing. A batch can use a published curriculum.',
    next: 'curriculum-subjects',
    action: 'Map semester subjects',
  },
  'curriculum-subjects': {
    description: 'Mark common subjects Required. Optional mappings can be grouped into complete alternatives.',
    next: 'curriculum-options',
    action: 'Define subject options',
  },
  'curriculum-options': {
    description:
      'After saving your options, review the curriculum and publish it. Publishing preserves its mappings and options.',
    next: 'curriculum-versions',
    action: 'Review and publish curriculum',
  },
  'curriculum-history': {
    description: 'Published versions remain assigned to their original batches.',
    next: 'cohorts',
    action: 'Manage admission batches',
  },
  cohorts: {
    description:
      'Choose a published curriculum for the admission intake, then organize its classes for a teaching term.',
    next: 'sections',
    action: 'Create academic sections',
  },
  sections: {
    description:
      'Connect a batch, study semester and dated teaching term. Next, offer the subjects that class can take.',
    next: 'offerings',
    action: 'Offer section subjects',
  },
  offerings: {
    description: 'Offer every required subject and every subject in the options you want students to choose.',
    next: 'enrollments',
    action: 'Assign students to sections',
  },
  enrollments: {
    description:
      'Assign approved students to a section. They then open Semester Registration in their student portal to choose an option.',
    next: 'offerings',
    action: 'Review subject availability',
  },
}

export function academicGuidance(page: AcademicPage) {
  return guidance[page]
}

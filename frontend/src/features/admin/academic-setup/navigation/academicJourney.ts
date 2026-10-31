import type { AcademicPage } from '../overview/academicOverviewModel.ts'

export const academicJourney = [
  {
    id: 'foundation',
    title: 'Foundations',
    page: 'departments',
    pages: ['departments', 'programs', 'calendar', 'years', 'terms', 'calendar-dates', 'calendar-timeline', 'subjects'],
    description: 'Create programs, set dated teaching periods, and add reusable subjects.',
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
      'program-semesters',
      'curriculum-history',
      'curriculum-existing',
    ],
    description: 'Build each program’s semester-by-semester subject plan, then publish it.',
  },
  {
    id: 'batches',
    title: 'Batches',
    page: 'cohorts',
    pages: ['cohorts'],
    description: 'Create an intake batch and assign its published curriculum.',
  },
  {
    id: 'delivery',
    title: 'Classes & subjects',
    page: 'sections',
    pages: ['sections', 'offerings'],
    description: 'Create the class groups you need for a batch, then offer their subjects.',
  },
  {
    id: 'enrollment',
    title: 'Student enrollment',
    page: 'enrollments',
    pages: ['enrollments'],
    description: 'Assign students to class groups; students then register their subject options.',
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
    next: 'subjects',
    action: 'Manage subjects',
  },
  years: {
    description: 'Add the dated teaching terms within each academic year.',
    next: 'terms',
    action: 'Configure academic terms',
  },
  terms: {
    description:
      'These dated teaching periods say when classes run; curriculum semesters say where students are in their degree.',
    next: 'subjects',
    action: 'Manage subjects',
  },
  subjects: {
    description:
      'Your subjects are ready. Next, create a study plan and choose which subjects belong in each semester.',
    next: 'curriculum-versions',
    action: 'Prepare a curriculum',
  },
  curriculum: {
    description: 'Create a draft study plan, choose subjects for each semester, then review and publish it.',
    next: 'curriculum-subjects',
    action: 'Choose semester subjects',
  },
  'curriculum-versions': {
    description:
      'After creating a draft, choose what students study in each semester. Publish when the study plan is ready.',
    next: 'curriculum-subjects',
    action: 'Choose semester subjects',
  },
  'curriculum-subjects': {
    description:
      'Set up the program’s numbered study stages here, then assign compulsory subjects and student choice groups. These stages are separate from dated teaching periods.',
    next: 'curriculum-versions',
    action: 'Back to curriculum list',
  },
  'curriculum-history': {
    description: 'Published versions remain assigned to their original batches.',
    next: 'cohorts',
    action: 'Manage admission batches',
  },
  cohorts: {
    description:
      'A batch is an intake group with one published curriculum. Create sections only when you need class groups for teaching or enrollment.',
    next: 'sections',
    action: 'Set up sections (optional)',
  },
  sections: {
    description:
      'Each section connects a batch, one program semester and one dated teaching term. Next, offer the subjects that class group can take.',
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
  return guidance[page === 'curriculum-options' || page === 'program-semesters' ? 'curriculum-subjects' : page]
}

interface AcademicDistinction {
  title: string
  description: string
}

const calendarPages: AcademicPage[] = ['calendar', 'years', 'terms', 'calendar-dates', 'calendar-timeline']
const progressionPages: AcademicPage[] = ['curriculum-subjects', 'curriculum-options', 'program-semesters']
const distinctionByPage: Partial<Record<AcademicPage, AcademicDistinction>> = {
  calendar: {
    title: 'Calendar terms are about when',
    description:
      'These semesters have start and end dates. Curriculum semesters are numbered stages in a degree and hold the subject plan.',
  },
  'curriculum-subjects': {
    title: 'Curriculum semesters are about study progression',
    description:
      'Assign subjects to numbered degree stages here. Dated teaching terms live in Academic Calendar; sections later connect a stage to a teaching term.',
  },
  cohorts: {
    title: 'Batch and section are different',
    description:
      'A batch groups students admitted together and keeps their curriculum. A section is a class group for one program semester and teaching term; add sections only when needed.',
  },
  sections: {
    title: 'A section is a class group',
    description:
      'It links one batch, one program semester and one dated teaching term. Create a section for each group that needs its own enrollment and subject offerings.',
  },
}

export function academicDistinction(page: AcademicPage) {
  const destination = calendarPages.includes(page)
    ? 'calendar'
    : progressionPages.includes(page)
      ? 'curriculum-subjects'
      : page
  return distinctionByPage[destination]
}

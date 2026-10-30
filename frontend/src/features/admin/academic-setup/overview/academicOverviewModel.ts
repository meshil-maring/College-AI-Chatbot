import {
  BookOpen,
  Building2,
  CalendarDays,
  CalendarRange,
  FileStack,
  GraduationCap,
  Layers3,
  LibraryBig,
  ListTree,
  Network,
  Users,
  type LucideIcon,
} from 'lucide-react'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import type { StructureEntity } from '../../../../types/academicStructure.ts'
import { academicDestinations } from '../navigation/academicDestinations.ts'

export type AcademicPage =
  | 'overview'
  | 'departments'
  | 'programs'
  | 'calendar'
  | 'years'
  | 'terms'
  | 'calendar-dates'
  | 'calendar-timeline'
  | 'program-semesters'
  | 'subjects'
  | 'curriculum'
  | 'curriculum-versions'
  | 'curriculum-subjects'
  | 'curriculum-options'
  | 'curriculum-history'
  | 'curriculum-existing'
  | 'enrollments'
  | 'cohorts'
  | 'sections'
  | 'offerings'
  | 'records'

export interface AcademicArea {
  page: AcademicPage
  title: string
  icon: LucideIcon
  description: string
  action: string
  note: string
  entity?: AcademicEntity
  structureEntity?: StructureEntity
  children?: readonly AcademicPage[]
  statuses?: readonly string[]
}

export const academicAreas: readonly AcademicArea[] = [
  {
    page: 'departments',
    title: 'Departments',
    icon: Building2,
    description: 'Create and manage academic departments across your institution.',
    action: 'Manage Departments',
    note: 'The foundation of your academic structure.',
    entity: 'departments',
  },
  {
    page: 'programs',
    title: 'Programs',
    icon: GraduationCap,
    description: 'Manage degree programs offered by each department.',
    action: 'Manage Programs',
    note: 'Degree programs, organized by department.',
    entity: 'programs',
  },
  {
    page: 'calendar',
    title: 'Academic Calendar',
    icon: CalendarDays,
    description: 'Configure academic years and dated teaching terms.',
    action: 'Manage Calendar',
    note: 'Your institution’s teaching calendar.',
    children: ['years', 'terms', 'calendar-dates', 'calendar-timeline'],
  },
  {
    page: 'subjects',
    title: 'Subjects',
    icon: BookOpen,
    description: 'Maintain your subject catalogue and subject details.',
    action: 'Manage Subjects',
    note: 'Reusable subjects across your institution.',
    entity: 'courses',
  },
  {
    page: 'program-semesters',
    structureEntity: 'program_semesters',
    title: 'Program Semesters',
    icon: Layers3,
    description: 'Define progression stages within each program, separate from dated academic terms.',
    action: 'Manage Program Semesters',
    note: 'Program progression: Semester 1, 2, …',
  },
  {
    page: 'curriculum',
    title: 'Curriculum',
    icon: FileStack,
    description: 'Define curriculum versions and their individual subject mappings.',
    action: 'Manage Curriculum',
    note: 'Published structures, preserved over time.',
    children: [
      'curriculum-versions',
      'curriculum-subjects',
      'curriculum-options',
      'curriculum-history',
      'curriculum-existing',
    ],
  },
  {
    page: 'cohorts',
    structureEntity: 'admission_cohorts',
    title: 'Batches',
    icon: Users,
    description: 'Group students by admission intake and retain their assigned published curriculum.',
    action: 'Manage Batches',
    note: 'Published curriculum assignment retained.',
    statuses: ['Planned', 'Active', 'Closed', 'Cancelled'],
  },
  {
    page: 'sections',
    structureEntity: 'academic_sections',
    title: 'Academic Sections',
    icon: Network,
    description: 'Organize a cohort within one program semester and one academic term.',
    action: 'Manage Academic Sections',
    note: 'One section can contain multiple subject offerings.',
    statuses: ['Planned', 'Active', 'Closed', 'Cancelled'],
  },
  {
    page: 'offerings',
    structureEntity: 'academic_offerings',
    title: 'Academic Offerings',
    icon: LibraryBig,
    description: 'Manage individual subject offerings within academic sections.',
    action: 'Manage Academic Offerings',
    note: 'Subject delivery, distinct from section grouping.',
    statuses: ['Planned', 'Active', 'Closed', 'Cancelled'],
  },
]

const childAreas: readonly AcademicArea[] = [
  {
    page: 'years',
    title: 'Academic Years',
    icon: CalendarDays,
    entity: 'academic_years',
    description: 'Configure institution-wide academic years and their date ranges.',
    action: 'Manage Academic Years',
    note: 'Calendar years are distinct from admission intakes.',
  },
  {
    page: 'terms',
    title: 'Academic Terms',
    icon: CalendarRange,
    description: 'Configure dated teaching periods within an academic year.',
    action: 'Manage Academic Terms',
    note: 'Academic terms describe when teaching takes place, not program progression.',
    statuses: ['Planned', 'Active', 'Closed', 'Cancelled'],
  },
  {
    page: 'curriculum-versions',
    structureEntity: 'curriculum_versions',
    title: 'Curriculum Versions',
    icon: FileStack,
    description: 'Prepare and publish a program’s curriculum structure.',
    action: 'Create Curriculum Version',
    note: 'A cohort retains its assigned published curriculum.',
    statuses: ['Draft', 'Published'],
  },
  {
    page: 'curriculum-subjects',
    structureEntity: 'curriculum_subjects',
    title: 'Curriculum Subjects',
    icon: ListTree,
    description: 'Manage subject mappings within a curriculum version.',
    action: 'Manage Curriculum Subjects',
    note: 'Subject mappings are distinct from the curriculum version itself.',
  },
]

export const allAcademicAreas = [...academicAreas, ...childAreas, ...academicDestinations]
export const getAcademicArea = (page: AcademicPage) => allAcademicAreas.find((area) => area.page === page)
export const summaryPages: readonly AcademicPage[] = ['departments', 'programs', 'subjects', 'years']
export const managementRows = [academicAreas.slice(0, 4), academicAreas.slice(4, 7), academicAreas.slice(7)]
export const sampleActivities = [
  'Department updated',
  'Program created',
  'Academic term configured',
  'Curriculum version published',
  'Admission cohort created',
  'Academic section activated',
  'Subject offering created',
]
export const quickActions: readonly { page: AcademicPage; label: string }[] = [
  { page: 'departments', label: 'Add Department' },
  { page: 'programs', label: 'Add Program' },
  { page: 'years', label: 'Configure Academic Year' },
  { page: 'subjects', label: 'Add Subject' },
  { page: 'curriculum-versions', label: 'Manage Curriculum Versions' },
  { page: 'cohorts', label: 'Manage Batches' },
  { page: 'sections', label: 'Manage Sections' },
  { page: 'offerings', label: 'Manage Offerings' },
]

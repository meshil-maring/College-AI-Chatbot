import { BookOpen, CalendarDays, ClipboardList, GraduationCap, Landmark, Layers, LibraryBig, Users } from 'lucide-react'
import type { AcademicEntity } from '../../../types/academicSetup.ts'

export const entityTitles: Record<AcademicEntity, string> = {
  departments: 'Departments',
  programs: 'Degree programs',
  academic_years: 'Academic Years',
  semesters: 'Teaching terms',
  courses: 'Subjects',
  program_courses: 'Curriculum',
  course_offerings: 'Offerings',
  sections: 'Sections',
  batches: 'Batches',
}
export const entitySingular: Record<AcademicEntity, string> = {
  departments: 'Department',
  programs: 'Program',
  academic_years: 'Academic Year',
  semesters: 'Teaching term',
  courses: 'Subject',
  program_courses: 'Curriculum Link',
  course_offerings: 'Offering',
  sections: 'Section',
  batches: 'Batch',
}
export const entityIcons = {
  departments: Landmark,
  programs: GraduationCap,
  academic_years: CalendarDays,
  semesters: Layers,
  courses: BookOpen,
  program_courses: LibraryBig,
  course_offerings: ClipboardList,
  sections: Users,
  batches: Users,
}

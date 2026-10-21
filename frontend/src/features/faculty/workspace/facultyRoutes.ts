import type { FacultyView } from './facultyNavigation.ts'
import type { StudentPage } from '../../students/studentsNavigation.ts'

export const FACULTY_PATHS: Readonly<Record<FacultyView, string>> = {
  dashboard: '/faculty',
  assignments: '/faculty/assignments',
  students: '/faculty/students',
  attendance: '/faculty/attendance',
  results: '/faculty/results',
  notices: '/faculty/notices',
  resources: '/faculty/resources',
  assistant: '/faculty/assistant',
  profile: '/faculty/profile',
  'class-management': '/faculty/class-management',
  department: '/faculty/department',
  'teaching-assignment-management': '/faculty/teaching-assignments',
}

export const STUDENT_REGISTRATION_PATH = '/faculty/students/register'
export type FacultyStudentPage = StudentPage
export const FACULTY_STUDENT_PATHS: Readonly<Record<FacultyStudentPage, string>> = {
  roster: '/faculty/students/roster',
  history: '/faculty/students/record-history',
  'waiting-approval': '/faculty/students/waiting-approval',
  register: STUDENT_REGISTRATION_PATH,
}

export function resolveFacultyRoute(pathname: string): { view: FacultyView; registerStudent: boolean; studentPage?: FacultyStudentPage } | null {
  const path = pathname.replace(/\/+$/, '')
  const studentPage = (Object.keys(FACULTY_STUDENT_PATHS) as FacultyStudentPage[]).find((page) => FACULTY_STUDENT_PATHS[page] === path)
  if (studentPage) return { view: 'students', registerStudent: studentPage === 'register', studentPage }
  const match = (Object.keys(FACULTY_PATHS) as FacultyView[]).find((view) => FACULTY_PATHS[view] === path)
  return match ? { view: match, registerStudent: false } : null
}

export function facultyStudentsPath(sectionId?: string, page: FacultyStudentPage = 'roster') {
  const path = FACULTY_STUDENT_PATHS[page]
  return sectionId ? `${path}?${new URLSearchParams({ section_id: sectionId })}` : path
}

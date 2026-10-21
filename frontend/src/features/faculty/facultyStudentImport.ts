import type { FacultyAttendanceRosterRow } from '../../services/facultyAttendanceApi.ts'
import { getClassStudentRegistrations, type ClassStudentRegistration } from '../../services/studentRegistrationApi.ts'
import { readStudentFile, type ImportStudent, type ReviewStudent } from '../admin/students/studentImport.ts'

export const REGISTRATION_COLUMNS = ['name', 'register_number', 'university_roll_number', 'email']

export function readRegistrationFile(file: File) {
  return readStudentFile(file, { requiredColumns: ['name', 'register_number', 'email'], allowedColumns: REGISTRATION_COLUMNS })
}

export async function loadRegistrationRoster(token: string, sectionId: string, getRegistrations = getClassStudentRegistrations): Promise<ClassStudentRegistration[]> {
  const students: ClassStudentRegistration[] = []
  for (let offset = 0; offset < 100_000; offset += 100) {
    const page = await getRegistrations(token, sectionId, offset)
    students.push(...page.items)
    if (students.length >= page.total) return students
    if (page.items.length < 100) throw new Error('The full section roster could not be loaded. Refresh the roster before importing.')
  }
  throw new Error('This section is too large to check for duplicates. Contact your administrator.')
}

const key = (value: string | null) => (value ?? '').trim().toLowerCase()
const identity = (row: ImportStudent) => JSON.stringify([row.name, row.registerNumber, row.rollNumber, row.email].map(key))

/** File review is advisory; the registration endpoint rechecks identity and scope. */
export function reviewStudentRegistrations(rows: ImportStudent[], existing: Pick<FacultyAttendanceRosterRow, 'register_number' | 'student_name' | 'university_roll_number' | 'email'>[]): ReviewStudent[] {
  return rows.map((row) => {
    const errors: string[] = []
    if (!row.name) errors.push('Student name is missing')
    if (!row.registerNumber) errors.push('Register number is missing')
    if (!row.email) errors.push('Student email is required')
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email)) errors.push('Email format is invalid')
    if (row.name.length > 256 || [row.registerNumber, row.rollNumber, row.email].some((value) => value.length > 128)) errors.push('A value exceeds the allowed length')
    if (errors.length) return { ...row, status: 'invalid', message: errors.join('; ') }
    const matches = existing.filter((student) => key(student.register_number) === key(row.registerNumber)
      || (!!row.rollNumber && key(student.university_roll_number) === key(row.rollNumber)))
    if (matches.length) {
      const conflict = matches.length > 1 || matches.some((student) => key(student.register_number) !== key(row.registerNumber)
        || key(student.student_name) !== key(row.name)
        || (!!row.rollNumber && !!student.university_roll_number && key(student.university_roll_number) !== key(row.rollNumber))
        || (!!row.email && !!student.email && key(student.email) !== key(row.email)))
      return { ...row, status: conflict ? 'conflicting' : 'duplicate', message: conflict ? 'Student identifiers exist with different details in this section' : 'Student already exists in this section' }
    }
    const related = rows.filter((other) => key(other.registerNumber) === key(row.registerNumber)
      || (!!row.rollNumber && key(other.rollNumber) === key(row.rollNumber)))
    if (related.some((other) => identity(other) !== identity(row))) return { ...row, status: 'conflicting', message: 'Student identifiers repeat with different details in this file' }
    if (related.some((other) => other.row < row.row)) return { ...row, status: 'duplicate', message: 'Repeated student record in this file' }
    return { ...row, status: 'valid', message: 'Ready for registration' }
  })
}

import type { StudentInvitationInput } from '../../../../types/admin/students.ts'

export type StudentField = keyof StudentInvitationInput
export type StudentFieldErrors = Partial<Record<StudentField, string>>

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Client-side checks that mirror what the server requires; the server remains authoritative. */
export function validateStudent(student: StudentInvitationInput): StudentFieldErrors {
  const errors: StudentFieldErrors = {}
  if (!student.student_name.trim()) errors.student_name = 'Enter the student’s full name.'
  if (!student.register_number.trim()) errors.register_number = 'Enter the register number.'
  const email = student.email.trim()
  if (!email) errors.email = 'Enter the email address that will receive the setup link.'
  else if (!EMAIL_PATTERN.test(email)) errors.email = 'Enter a valid email address, like name@college.edu.'
  return errors
}

/** Field order used to move focus to the first problem. */
export const STUDENT_FIELD_ORDER: StudentField[] = [
  'student_name',
  'register_number',
  'university_roll_number',
  'email',
]

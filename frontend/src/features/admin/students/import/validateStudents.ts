import type { Student } from '../../../../types/admin.ts'
import { type ImportStudent, type ReviewStudent } from './types.ts'
export const key = (value: string) => value.trim().toLowerCase()

export const identity = (row: ImportStudent) =>
  JSON.stringify([row.name, row.registerNumber, row.rollNumber, row.email].map(key))

/** These are file checks, not server approval or authorization to create an account. */
export function validateStudents(rows: ImportStudent[], existing: Student[]): ReviewStudent[] {
  const registered = new Set(existing.map((student) => key(student.student_number)))
  const groups = new Map<string, ImportStudent[]>()
  for (const row of rows) {
    for (const value of [
      `register:${key(row.registerNumber)}`,
      `roll:${key(row.rollNumber)}`,
      `email:${key(row.email)}`,
    ]) {
      if (!value.split(':').slice(1).join(':')) continue
      groups.set(value, [...(groups.get(value) ?? []), row])
    }
  }
  return rows.map((row) => {
    const errors: string[] = []
    if (!row.name) errors.push('Name is missing')
    if (!row.registerNumber) errors.push('Register number is missing')
    if (!row.rollNumber) errors.push('University roll number is missing')
    if (!row.email) errors.push('Email is missing')
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email)) errors.push('Email format is invalid')
    if (
      row.name.length > 256 ||
      row.registerNumber.length > 128 ||
      row.rollNumber.length > 128 ||
      row.email.length > 128
    )
      errors.push('A value exceeds the allowed length')
    if (
      row.attendance &&
      (!Number.isFinite(Number(row.attendance)) || Number(row.attendance) < 0 || Number(row.attendance) > 100)
    )
      errors.push('Attendance must be between 0 and 100')
    if (errors.length) return { ...row, status: 'invalid', message: errors.join('; ') }
    const matches = [
      `register:${key(row.registerNumber)}`,
      `roll:${key(row.rollNumber)}`,
      `email:${key(row.email)}`,
    ].flatMap((value) => groups.get(value) ?? [])
    const collided = [
      [`register:${key(row.registerNumber)}`, 'Register number'],
      [`roll:${key(row.rollNumber)}`, 'University roll number'],
      [`email:${key(row.email)}`, 'Email'],
    ].find(([value]) => (groups.get(value) ?? []).some((other) => identity(other) !== identity(row)))
    if (collided)
      return {
        ...row,
        status: 'conflicting',
        message: `${collided[1]} exists with different details`,
      }
    if (registered.has(key(row.registerNumber)))
      return {
        ...row,
        status: 'duplicate',
        message: 'Register number already exists',
      }
    if (matches.some((other) => other.row < row.row))
      return {
        ...row,
        status: 'duplicate',
        message: 'Repeated student record in this file',
      }
    return { ...row, status: 'valid', message: 'All fields valid' }
  })
}

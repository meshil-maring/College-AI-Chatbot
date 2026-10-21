export type ReviewStatus = 'valid' | 'duplicate' | 'invalid' | 'conflicting'

export interface ImportStudent {
  row: number
  name: string
  registerNumber: string
  rollNumber: string
  email: string
  attendance: string
}

export interface ReviewStudent extends ImportStudent {
  status: ReviewStatus
  message: string
}

export const IMPORT_LIMIT = 1000

export const IMPORT_COLUMNS = ['name', 'register_number', 'university_roll_number', 'email', 'attendance']

export const aliases: Record<string, string> = {
  student_name: 'name',
  full_name: 'name',
  register_no: 'register_number',
  registration_number: 'register_number',
  student_number: 'register_number',
  university_roll_no: 'university_roll_number',
  roll_number: 'university_roll_number',
  attendance_percent: 'attendance',
  attendance_percentage: 'attendance',
}

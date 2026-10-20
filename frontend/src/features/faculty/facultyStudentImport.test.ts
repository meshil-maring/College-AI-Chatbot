import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getFacultyAttendanceStudents, type FacultyAttendanceRosterRow } from '../../services/facultyAttendanceApi.ts'
import { parseCsv, readImportRows, type ImportStudent } from '../admin/students/studentImport.ts'
import { loadRegistrationRoster, REGISTRATION_COLUMNS, reviewStudentRegistrations } from './facultyStudentImport.ts'

vi.mock('../../services/facultyAttendanceApi.ts', () => ({ getFacultyAttendanceStudents: vi.fn() }))
const row = (overrides: Partial<ImportStudent> = {}): ImportStudent => ({ row: 2, name: 'Ada Rao', registerNumber: '001', rollNumber: '', email: '', attendance: '', ...overrides })
const existing: FacultyAttendanceRosterRow = { roster_id: 'r1', student_name: 'Ada Rao', register_number: '001', university_roll_number: null, email: null, roster_status: 'UNREGISTERED', linked_student_id: null }
beforeEach(() => vi.resetAllMocks())

describe('bulk student registration review', () => {
  it('supports optional contact and roll fields, preserves identifier zeros, and rejects unsupported attendance columns', () => {
    const options = { requiredColumns: ['name', 'register_number'], allowedColumns: REGISTRATION_COLUMNS }
    expect(readImportRows(parseCsv('student_name,register_number\nAda Rao,001'), options)).toEqual([row()])
    expect(() => readImportRows(parseCsv('name,register_number,attendance\nAda Rao,001,90'), options)).toThrow('Unrecognized columns: attendance')
    expect(reviewStudentRegistrations([row()], [])[0].status).toBe('valid')
  })
  it('distinguishes identical duplicates, conflicting identities, malformed email, and missing required fields', () => {
    expect(reviewStudentRegistrations([row()], [existing])[0].status).toBe('duplicate')
    expect(reviewStudentRegistrations([row({ name: 'Other Student' })], [existing])[0].status).toBe('conflicting')
    expect(reviewStudentRegistrations([row({ registerNumber: '002', rollNumber: 'UNI1' })], [{ ...existing, university_roll_number: 'UNI1' }])[0].status).toBe('conflicting')
    expect(reviewStudentRegistrations([row(), row({ row: 3 })], []).map((item) => item.status)).toEqual(['valid', 'duplicate'])
    expect(reviewStudentRegistrations([row(), row({ row: 3, name: 'Other Student' })], []).map((item) => item.status)).toEqual(['conflicting', 'conflicting'])
    expect(reviewStudentRegistrations([row({ name: '', email: 'invalid' })], [])[0]).toMatchObject({ status: 'invalid', message: 'Student name is missing; Email format is invalid' })
  })
  it('loads all section roster pages and refuses incomplete duplicate checks', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValueOnce({ items: Array.from({ length: 100 }, () => existing), total: 101 }).mockResolvedValueOnce({ items: [existing], total: 101 })
    expect(await loadRegistrationRoster('token', 'section-1')).toHaveLength(101)
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('100')
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [], total: 10 })
    await expect(loadRegistrationRoster('token', 'section-1')).rejects.toThrow('full section roster could not be loaded')
  })
})

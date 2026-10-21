import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getClassStudentRegistrations, type ClassStudentRegistration } from '../../../../services/students/studentRegistrationApi.ts'
import { parseCsv, readImportRows, type ImportStudent } from '../../../admin/students/studentImport.ts'
import { loadRegistrationRoster, REGISTRATION_COLUMNS, reviewStudentRegistrations } from './facultyStudentImport.ts'

vi.mock('../../../../services/students/studentRegistrationApi.ts', () => ({ getClassStudentRegistrations: vi.fn() }))
const row = (overrides: Partial<ImportStudent> = {}): ImportStudent => ({ row: 2, name: 'Ada Rao', registerNumber: '001', rollNumber: '', email: 'ada@college.edu', attendance: '', ...overrides })
const existing: ClassStudentRegistration = { registration_id: 'r1', batch_id: 'batch-1', program_id: 'program-1', section_code: 'A', batch_start_year: 2026, batch_end_year: 2030, identity_conflict: false, subjects_assigned: false, student_name: 'Ada Rao', register_number: '001', university_roll_number: null, email: null, roster_status: 'UNREGISTERED', linked_student_id: null }
beforeEach(() => vi.resetAllMocks())

describe('bulk student registration review', () => {
  it('requires email while allowing an optional roll number and preserves identifier zeros', () => {
    const options = { requiredColumns: ['name', 'register_number', 'email'], allowedColumns: REGISTRATION_COLUMNS }
    expect(readImportRows(parseCsv('student_name,register_number,email\nAda Rao,001,ada@college.edu'), options)).toEqual([row()])
    expect(() => readImportRows(parseCsv('name,register_number,email,attendance\nAda Rao,001,ada@college.edu,90'), options)).toThrow('Unrecognized columns: attendance')
    expect(() => readImportRows(parseCsv('name,register_number\nAda Rao,001'), options)).toThrow('Missing columns: email')
    expect(reviewStudentRegistrations([row({ email: '' })], [])[0]).toMatchObject({ status: 'invalid', message: 'Student email is required' })
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
    vi.mocked(getClassStudentRegistrations).mockResolvedValueOnce({ items: Array.from({ length: 100 }, () => existing), total: 101 }).mockResolvedValueOnce({ items: [existing], total: 101 })
    expect(await loadRegistrationRoster('token', 'section-1')).toHaveLength(101)
    expect(vi.mocked(getClassStudentRegistrations).mock.lastCall?.[2]).toBe(100)
    vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [], total: 10 })
    await expect(loadRegistrationRoster('token', 'section-1')).rejects.toThrow('full section roster could not be loaded')
  })
})

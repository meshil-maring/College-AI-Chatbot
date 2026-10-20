import { describe, expect, it } from 'vitest'
import type { Student } from '../../../types/admin.ts'
import {
  IMPORT_COLUMNS,
  parseCsv,
  readImportRows,
  toCsv,
  validateStudents,
  type ImportStudent,
} from './studentImport.ts'

const student = (overrides: Partial<ImportStudent> = {}): ImportStudent => ({
  row: 2,
  name: 'Test Student',
  registerNumber: 'REG001',
  rollNumber: 'ROLL001',
  email: 'student@example.test',
  attendance: '92',
  ...overrides,
})

describe('student import file review', () => {
  it('reads BOM, CRLF, embedded commas/newlines, escaped quotes and leading zeros', () => {
    const rows = parseCsv(
      '\uFEFFname,register_number,university_roll_number,email,attendance\r\n"Test, ""Student""\nName",001,0002,test@example.test,0\r\n',
    )
    expect(readImportRows(rows)[0]).toEqual(
      student({
        name: 'Test, "Student"\nName',
        registerNumber: '001',
        rollNumber: '0002',
        email: 'test@example.test',
        attendance: '0',
      }),
    )
  })
  it('rejects broken quotes and unknown, missing or repeated columns', () => {
    expect(() => parseCsv('"unfinished')).toThrow('incomplete')
    expect(() => readImportRows([['name'], ['Student']])).toThrow(
      'Missing columns',
    )
    expect(() => readImportRows([[...IMPORT_COLUMNS, 'password'], []])).toThrow(
      'Unrecognized columns',
    )
    expect(() =>
      readImportRows([[...IMPORT_COLUMNS, 'student_name'], []]),
    ).toThrow('unique')
    expect(() =>
      readImportRows([IMPORT_COLUMNS, ['a', 'b', 'c', 'd', 'e', 'extra']]),
    ).toThrow('Row 2')
  })
  it('retains spreadsheet row numbers, normalizes email and accepts attendance zero', () => {
    const rows = readImportRows([
      IMPORT_COLUMNS,
      [],
      ['Student', '001', 'U001', ' TEST@EXAMPLE.TEST ', '0'],
    ])
    expect(rows[0]).toMatchObject({
      row: 3,
      registerNumber: '001',
      email: 'test@example.test',
      attendance: '0',
    })
    expect(validateStudents(rows, [])[0]).toMatchObject({
      status: 'valid',
      message: 'All fields valid',
    })
  })
  it('separates existing records, identical repeats, conflicting identifiers and invalid fields', () => {
    expect(
      validateStudents(
        [student()],
        [{ student_number: 'reg001' } as Student],
      )[0],
    ).toMatchObject({
      status: 'duplicate',
      message: 'Register number already exists',
    })
    expect(
      validateStudents([student(), student({ row: 3 })], []).map(
        (row) => row.status,
      ),
    ).toEqual(['valid', 'duplicate'])
    const conflicting = validateStudents(
      [student(), student({ row: 3, name: 'Different Name' })],
      [],
    )
    expect(conflicting.map((row) => row.status)).toEqual([
      'conflicting',
      'conflicting',
    ])
    expect(conflicting[0].message).toBe(
      'Register number exists with different details',
    )
    const invalid = validateStudents(
      [student({ rollNumber: '', email: 'bad-email', attendance: '101' })],
      [],
    )[0]
    expect(invalid.status).toBe('invalid')
    expect(invalid.message).toContain('University roll number is missing')
    expect(invalid.message).toContain('Email format is invalid')
    expect(invalid.message).toContain('Attendance must be between 0 and 100')
  })
  it('detects email or roll-number collisions even when register numbers differ', () => {
    expect(
      validateStudents(
        [
          student(),
          student({
            row: 3,
            registerNumber: 'REG002',
            email: 'other@example.test',
          }),
        ],
        [],
      ).every((row) => row.status === 'conflicting'),
    ).toBe(true)
    expect(
      validateStudents(
        [
          student(),
          student({ row: 3, registerNumber: 'REG002', rollNumber: 'ROLL002' }),
        ],
        [],
      ).every((row) => row.status === 'conflicting'),
    ).toBe(true)
  })
  it('quotes report values and neutralizes spreadsheet formulas', () => {
    expect(toCsv([['=1+1', ' @SUM(A1)', 'a,"b"', '001']])).toBe(
      '\uFEFF"\'=1+1","\' @SUM(A1)","a,""b""","001"',
    )
  })
  it('rejects empty or excessively large imports', () => {
    expect(() => readImportRows([IMPORT_COLUMNS])).toThrow('No student records')
    expect(() =>
      readImportRows([
        IMPORT_COLUMNS,
        ...Array.from({ length: 1001 }, () => [
          'Name',
          'REG',
          'ROLL',
          'a@example.test',
        ]),
      ]),
    ).toThrow('1,000')
  })
})

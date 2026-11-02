import { describe, expect, it, vi } from 'vitest'
import { parseStudentFile, validateStudentRows } from './studentImport.ts'

vi.mock('read-excel-file/browser', () => ({
  default: vi.fn().mockResolvedValue([{
    data: [
      ['Student Name', 'Register Number', 'Email'],
      ['Ada Lovelace', 'REG-1', 'ada@example.com'],
    ],
  }]),
}))

function csvFile(contents: string) {
  return new File([contents], 'students.csv', { type: 'text/csv' })
}

describe('student import review', () => {
  it('parses quoted CSV values and maps the optional university roll number', async () => {
    const rows = await parseStudentFile(csvFile(
      'Student Name,Register Number,University Roll No.,Email\r\n"Ada, Lovelace",REG-1,UNI-1,ADA@EXAMPLE.TEST',
    ))

    expect(rows).toEqual([{
      sourceRow: 2,
      student_name: 'Ada, Lovelace',
      register_number: 'REG-1',
      university_roll_number: 'UNI-1',
      email: 'ada@example.test',
      errors: [],
    }])
  })

  it('reads the first worksheet from an Excel upload', async () => {
    const rows = await parseStudentFile(new File(['xlsx'], 'students.xlsx'))

    expect(rows[0]).toMatchObject({
      sourceRow: 2,
      student_name: 'Ada Lovelace',
      register_number: 'REG-1',
      email: 'ada@example.com',
      errors: [],
    })
  })

  it('requires all mandatory headers', async () => {
    await expect(parseStudentFile(csvFile('Other,Email\nAda,ada@example.test')))
      .rejects.toThrow('Missing required columns: student_name, register_number.')
  })

  it('marks duplicate identities and invalid email addresses for review', () => {
    const rows = validateStudentRows([
      { sourceRow: 2, student_name: 'Ada', register_number: 'REG-1', university_roll_number: '', email: 'ada@example.test', errors: [] },
      { sourceRow: 3, student_name: 'Grace', register_number: 'reg-1', university_roll_number: '', email: 'not-an-email', errors: [] },
    ])

    expect(rows[0].errors).toEqual([])
    expect(rows[1].errors).toContain('Enter a valid email address.')
    expect(rows[1].errors).toContain('This row duplicates a value in the upload.')
  })

  it('does not report missing identity fields as duplicate values', () => {
    const [row] = validateStudentRows([{
      sourceRow: 2,
      student_name: '',
      register_number: '',
      university_roll_number: '',
      email: '',
      errors: [],
    }])

    expect(row.errors).toEqual(['Student Name is required.', 'Register Number is required.', 'Email is required.'])
  })

  it('rejects CSV with an unclosed quoted field', async () => {
    await expect(parseStudentFile(csvFile('Student Name,Register Number,Email\n"Ada,REG-1,ada@example.test')))
      .rejects.toThrow('unclosed quoted field')
  })
})

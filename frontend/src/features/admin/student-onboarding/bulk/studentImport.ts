import type { StudentInvitationInput } from '../../../../types/admin/students.ts'
import { normalizeCsvHeader as normalizeHeader, parseCsv } from '../../../../lib/csv.ts'

export interface StudentImportRow extends StudentInvitationInput {
  sourceRow: number
  errors: string[]
}

const REQUIRED_HEADERS = ['student_name', 'register_number', 'email'] as const
const HEADER_ALIASES: Record<string, keyof StudentInvitationInput> = {
  studentname: 'student_name',
  name: 'student_name',
  registernumber: 'register_number',
  universityrollno: 'university_roll_number',
  universityrollnumber: 'university_roll_number',
  email: 'email',
}

function rowValue(row: unknown[], index: number | undefined): string {
  if (index === undefined) return ''
  const value = row[index]
  return value == null ? '' : String(value).trim()
}

export function validateStudentRows(rows: StudentImportRow[]): StudentImportRow[] {
  const seen = new Set<string>()
  return rows.map((row) => {
    const errors: string[] = []
    if (!row.student_name.trim()) errors.push('Student Name is required.')
    if (!row.register_number.trim()) errors.push('Register Number is required.')
    if (!row.email.trim()) errors.push('Email is required.')
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email.trim())) errors.push('Enter a valid email address.')
    const email = row.email.trim().toLowerCase()
    const registerNumber = row.register_number.trim().toLowerCase()
    const universityRollNumber = (row.university_roll_number ?? '').trim().toLowerCase()
    const keys = [
      ...(email ? [`email:${email}`] : []),
      ...(registerNumber ? [`register:${registerNumber}`] : []),
      ...(universityRollNumber ? [`roll:${universityRollNumber}`] : []),
    ]
    if (keys.some((key) => seen.has(key))) errors.push('This row duplicates a value in the upload.')
    keys.forEach((key) => seen.add(key))
    return { ...row, errors }
  })
}

export async function parseStudentFile(file: File): Promise<StudentImportRow[]> {
  if (file.size > 5 * 1024 * 1024) throw new Error('Choose a file smaller than 5 MB.')
  const extension = file.name.split('.').pop()?.toLowerCase()
  const rawRows =
    extension === 'csv'
      ? parseCsv(await file.text(), 500, 'student rows')
      : extension === 'xlsx'
        ? (await import('read-excel-file/browser')).default(file).then((sheets) => sheets[0]?.data ?? [])
        : null
  const rowsFromFile = await rawRows
  if (!rowsFromFile) throw new Error('Choose a CSV or Excel (.xlsx) file.')
  if (rowsFromFile.length < 2) throw new Error('The file needs a header row and at least one student.')
  if (rowsFromFile.length > 501) throw new Error('Upload no more than 500 student rows at a time.')
  const headerIndexes = new Map<string, number>()
  rowsFromFile[0].forEach((header, index) => {
    const field = HEADER_ALIASES[normalizeHeader(header)]
    if (field) headerIndexes.set(field, index)
  })
  const missingHeaders = REQUIRED_HEADERS.filter((header) => !headerIndexes.has(header))
  if (missingHeaders.length) throw new Error(`Missing required columns: ${missingHeaders.join(', ')}.`)
  const rows = rowsFromFile.slice(1).map((cells, index) => ({
    sourceRow: index + 2,
    student_name: rowValue(cells, headerIndexes.get('student_name')),
    register_number: rowValue(cells, headerIndexes.get('register_number')),
    university_roll_number: rowValue(cells, headerIndexes.get('university_roll_number')),
    email: rowValue(cells, headerIndexes.get('email')).toLowerCase(),
    errors: [],
  }))
  return validateStudentRows(rows)
}

import type { Student } from '../../../types/admin.ts'

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
export const IMPORT_COLUMNS = [
  'name',
  'register_number',
  'university_roll_number',
  'email',
  'attendance',
]
const aliases: Record<string, string> = {
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

/** RFC 4180 quoting, including embedded newlines and escaped double quotes. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = [],
    cell = '',
    quoted = false,
    closed = false
  const source = text.replace(/^\uFEFF/, '')
  for (let i = 0; i < source.length; i++) {
    const char = source[i]
    if (quoted) {
      if (char === '"' && source[i + 1] === '"') {
        cell += '"'
        i++
      } else if (char === '"') {
        quoted = false
        closed = true
      } else cell += char
    } else if (char === '"') {
      if (cell || closed)
        throw new Error(
          'Unexpected quotation mark. Save the file as a standard CSV and try again.',
        )
      quoted = true
    } else if (char === ',') {
      row.push(cell)
      cell = ''
      closed = false
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && source[i + 1] === '\n') i++
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
      closed = false
    } else {
      if (closed && char.trim())
        throw new Error(
          'Unexpected text after a quoted value. Check the CSV formatting.',
        )
      if (!closed) cell += char
    }
  }
  if (quoted)
    throw new Error('A quoted value is incomplete. Check the CSV formatting.')
  if (cell || row.length || closed) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

export interface ImportFileOptions {
  requiredColumns?: readonly string[]
  allowedColumns?: readonly string[]
}

export function readImportRows(table: unknown[][], options: ImportFileOptions = {}): ImportStudent[] {
  const [heading, ...body] = table
  if (!heading?.length)
    throw new Error(
      'The file is empty. Add column headings and student records.',
    )
  const headers = heading.map((value) => {
    const key = String(value ?? '')
      .trim()
      .toLowerCase()
      .replace(/[%]/g, 'percent')
      .replace(/[\s-]+/g, '_')
    return aliases[key] ?? key
  })
  if (new Set(headers).size !== headers.length)
    throw new Error('Column headings must be unique.')
  const missing = (options.requiredColumns ?? IMPORT_COLUMNS.slice(0, 4)).filter(
    (column) => !headers.includes(column),
  )
  if (missing.length)
    throw new Error(
      `Missing columns: ${missing.join(', ')}. Download the template for the required format.`,
    )
  const unknown = headers.filter((column) => !(options.allowedColumns ?? IMPORT_COLUMNS).includes(column))
  if (unknown.length)
    throw new Error(
      `Unrecognized columns: ${unknown.join(', ')}. Use the template headings.`,
    )
  const rows = body
    .map((values, index) => ({ values, row: index + 2 }))
    .filter(({ values }) => values.some((value) => String(value ?? '').trim()))
  if (!rows.length)
    throw new Error('No student records were found in the file.')
  if (rows.length > IMPORT_LIMIT)
    throw new Error(
      `Upload up to ${IMPORT_LIMIT.toLocaleString()} records at a time.`,
    )
  return rows.map(({ values, row }) => {
    if (values.length > headers.length)
      throw new Error(`Row ${row} has more values than the column headings.`)
    const get = (column: string) =>
      String(values[headers.indexOf(column)] ?? '').trim()
    return {
      row,
      name: get('name'),
      registerNumber: get('register_number'),
      rollNumber: get('university_roll_number'),
      email: get('email').toLowerCase(),
      attendance: get('attendance').replace(/%$/, '').trim(),
    }
  })
}

export async function readStudentFile(file: File, options: ImportFileOptions = {}): Promise<ImportStudent[]> {
  if (file.size > 5 * 1024 * 1024)
    throw new Error('Choose a file smaller than 5 MB.')
  if (/\.csv$/i.test(file.name))
    return readImportRows(parseCsv(await file.text()), options)
  if (/\.xlsx$/i.test(file.name)) {
    const { readSheet } = await import('read-excel-file/browser')
    return readImportRows(await readSheet(file), options)
  }
  throw new Error('Choose an Excel (.xlsx) or CSV (.csv) file.')
}

const key = (value: string) => value.trim().toLowerCase()
const identity = (row: ImportStudent) =>
  JSON.stringify(
    [row.name, row.registerNumber, row.rollNumber, row.email].map(key),
  )

/** These are file checks, not server approval or authorization to create an account. */
export function validateStudents(
  rows: ImportStudent[],
  existing: Student[],
): ReviewStudent[] {
  const registered = new Set(
    existing.map((student) => key(student.student_number)),
  )
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
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email))
      errors.push('Email format is invalid')
    if (
      row.name.length > 256 ||
      row.registerNumber.length > 128 ||
      row.rollNumber.length > 128 ||
      row.email.length > 128
    )
      errors.push('A value exceeds the allowed length')
    if (
      row.attendance &&
      (!Number.isFinite(Number(row.attendance)) ||
        Number(row.attendance) < 0 ||
        Number(row.attendance) > 100)
    )
      errors.push('Attendance must be between 0 and 100')
    if (errors.length)
      return { ...row, status: 'invalid', message: errors.join('; ') }
    const matches = [
      `register:${key(row.registerNumber)}`,
      `roll:${key(row.rollNumber)}`,
      `email:${key(row.email)}`,
    ].flatMap((value) => groups.get(value) ?? [])
    const collided = [
      [`register:${key(row.registerNumber)}`, 'Register number'],
      [`roll:${key(row.rollNumber)}`, 'University roll number'],
      [`email:${key(row.email)}`, 'Email'],
    ].find(([value]) =>
      (groups.get(value) ?? []).some(
        (other) => identity(other) !== identity(row),
      ),
    )
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

/** Keep spreadsheet apps from interpreting exported user values as formulas. */
export function toCsv(rows: unknown[][]): string {
  return (
    '\uFEFF' +
    rows
      .map((row) =>
        row
          .map((value) => {
            const text = String(value ?? '')
            return (
              '"' +
              (/^[\s]*[=+\-@\t\r]/.test(text) ? "'" + text : text).replace(
                /"/g,
                '""',
              ) +
              '"'
            )
          })
          .join(','),
      )
      .join('\r\n')
  )
}

export function downloadCsv(name: string, rows: unknown[][]) {
  const url = URL.createObjectURL(
    new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }),
  )
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

import { type ImportStudent, IMPORT_COLUMNS, IMPORT_LIMIT, aliases } from './types.ts'
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
      if (cell || closed) throw new Error('Unexpected quotation mark. Save the file as a standard CSV and try again.')
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
      if (closed && char.trim()) throw new Error('Unexpected text after a quoted value. Check the CSV formatting.')
      if (!closed) cell += char
    }
  }
  if (quoted) throw new Error('A quoted value is incomplete. Check the CSV formatting.')
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
  if (!heading?.length) throw new Error('The file is empty. Add column headings and student records.')
  const headers = heading.map((value) => {
    const key = String(value ?? '')
      .trim()
      .toLowerCase()
      .replace(/[%]/g, 'percent')
      .replace(/[\s-]+/g, '_')
    return aliases[key] ?? key
  })
  if (new Set(headers).size !== headers.length) throw new Error('Column headings must be unique.')
  const missing = (options.requiredColumns ?? IMPORT_COLUMNS.slice(0, 4)).filter((column) => !headers.includes(column))
  if (missing.length)
    throw new Error(`Missing columns: ${missing.join(', ')}. Download the template for the required format.`)
  const unknown = headers.filter((column) => !(options.allowedColumns ?? IMPORT_COLUMNS).includes(column))
  if (unknown.length) throw new Error(`Unrecognized columns: ${unknown.join(', ')}. Use the template headings.`)
  const rows = body
    .map((values, index) => ({ values, row: index + 2 }))
    .filter(({ values }) => values.some((value) => String(value ?? '').trim()))
  if (!rows.length) throw new Error('No student records were found in the file.')
  if (rows.length > IMPORT_LIMIT) throw new Error(`Upload up to ${IMPORT_LIMIT.toLocaleString()} records at a time.`)
  return rows.map(({ values, row }) => {
    if (values.length > headers.length) throw new Error(`Row ${row} has more values than the column headings.`)
    const get = (column: string) => String(values[headers.indexOf(column)] ?? '').trim()
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
  if (file.size > 5 * 1024 * 1024) throw new Error('Choose a file smaller than 5 MB.')
  if (/\.csv$/i.test(file.name)) return readImportRows(parseCsv(await file.text()), options)
  if (/\.xlsx$/i.test(file.name)) {
    const { readSheet } = await import('read-excel-file/browser')
    return readImportRows(await readSheet(file), options)
  }
  throw new Error('Choose an Excel (.xlsx) or CSV (.csv) file.')
}

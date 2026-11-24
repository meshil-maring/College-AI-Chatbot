/** Minimal RFC 4180 CSV parsing shared by the admin import screens. */

/** Splits CSV text into trimmed-cell rows, skipping blank lines. */
export function parseCsv(text: string, maxRows: number, noun = 'rows'): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index]
    if (quoted && character === '"' && text[index + 1] === '"') {
      field += '"'
      index += 1
    } else if (character === '"') {
      quoted = !quoted
    } else if (!quoted && character === ',') {
      row.push(field)
      field = ''
    } else if (!quoted && (character === '\n' || character === '\r')) {
      row.push(field)
      if (row.some((cell) => cell.trim())) rows.push(row)
      row = []
      field = ''
      if (character === '\r' && text[index + 1] === '\n') index += 1
    } else {
      field += character
    }
    // The header row is allowed on top of the data limit.
    if (rows.length > maxRows) throw new Error(`Upload no more than ${maxRows} ${noun} at a time.`)
  }
  if (quoted) throw new Error('The CSV file contains an unclosed quoted field.')
  row.push(field)
  if (row.some((cell) => cell.trim())) rows.push(row)
  return rows
}

/** Lower-cases a header and strips spaces, punctuation and a byte-order mark. */
export function normalizeCsvHeader(value: unknown): string {
  return String(value ?? '')
    .replace(/﻿/g, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
}

/** Quotes a value for a CSV template or export. */
export function csvCell(value: string | number): string {
  const text = String(value)
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

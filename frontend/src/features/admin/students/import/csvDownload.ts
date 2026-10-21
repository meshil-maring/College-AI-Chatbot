/** Keep spreadsheet apps from interpreting exported user values as formulas. */
export function toCsv(rows: unknown[][]): string {
  return (
    '\uFEFF' +
    rows
      .map((row) =>
        row
          .map((value) => {
            const text = String(value ?? '')
            return '"' + (/^[\s]*[=+\-@\t\r]/.test(text) ? "'" + text : text).replace(/"/g, '""') + '"'
          })
          .join(','),
      )
      .join('\r\n')
  )
}

export function downloadCsv(name: string, rows: unknown[][]) {
  const url = URL.createObjectURL(new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
